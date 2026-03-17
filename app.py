from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pydub import AudioSegment
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import uuid
import logging
from langdetect import detect
import atexit
from threading import Lock
import time

app = Flask(__name__)
CORS(app)  # In production, configure with specific origins: CORS(app, origins=["http://localhost:3000"])

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['TEMP_DIR'] = "temp_audio"
app.config['MAX_FILE_AGE'] = 3600  # 1 hour in seconds

# Supported languages for translation and TTS
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-CN': 'Chinese (Simplified)',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize recognizer
recognizer = sr.Recognizer()

# Create temp directory if it doesn't exist
if not os.path.exists(app.config['TEMP_DIR']):
    os.makedirs(app.config['TEMP_DIR'])

# Thread lock for file operations
file_lock = Lock()

# -----------------------------------
# Cleanup Functions
# -----------------------------------
def cleanup_old_files():
    """Remove files older than MAX_FILE_AGE seconds"""
    try:
        current_time = time.time()
        for filename in os.listdir(app.config['TEMP_DIR']):
            file_path = os.path.join(app.config['TEMP_DIR'], filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > app.config['MAX_FILE_AGE']:
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old file: {filename}")
                    except Exception as e:
                        logger.error(f"Error cleaning up {filename}: {e}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def cleanup_all_temp_files():
    """Remove all temporary files on application exit"""
    try:
        for filename in os.listdir(app.config['TEMP_DIR']):
            file_path = os.path.join(app.config['TEMP_DIR'], filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing {filename}: {e}")
        logger.info("Cleaned up all temporary files")
    except Exception as e:
        logger.error(f"Exit cleanup error: {e}")

# Register cleanup on exit
atexit.register(cleanup_all_temp_files)

# -----------------------------------
# Error Handlers
# -----------------------------------
@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

# -----------------------------------
# Health Check
# -----------------------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "supported_languages": SUPPORTED_LANGUAGES
    })

# -----------------------------------
# Process Audio
# -----------------------------------
@app.route('/process-audio', methods=['POST'])
def process_audio():
    temp_files = []
    
    try:
        # Run cleanup occasionally (every 10 requests)
        if request.remote_addr:  # Simple way to trigger cleanup occasionally
            cleanup_old_files()

        # Validate audio file
        if 'audio' not in request.files:
            logger.warning("No audio file provided")
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio']
        
        # Validate filename
        if audio_file.filename == '':
            logger.warning("Empty filename provided")
            return jsonify({"error": "Empty filename"}), 400

        # Get and validate target language
        target_lang = request.form.get('target_lang', 'en')
        
        if target_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language requested: {target_lang}")
            return jsonify({
                "error": f"Unsupported language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
            }), 400

        logger.info(f"Processing audio for language: {target_lang}")

        # Generate unique IDs for files
        unique_id = uuid.uuid4()
        temp_webm = os.path.join(app.config['TEMP_DIR'], f"{unique_id}.webm")
        temp_wav = os.path.join(app.config['TEMP_DIR'], f"{unique_id}.wav")
        temp_files = [temp_webm, temp_wav]

        # Save uploaded file
        audio_file.save(temp_webm)
        logger.debug(f"Saved audio to {temp_webm}")

        # Convert WebM to WAV
        try:
            with file_lock:
                audio = AudioSegment.from_file(temp_webm, format="webm")
                audio.export(temp_wav, format="wav")
            logger.debug("Audio converted to WAV")
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            return jsonify({"error": "Audio format not supported or corrupted"}), 400

        # Speech Recognition
        try:
            with sr.AudioFile(temp_wav) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)
            
            # Try different recognition engines
            try:
                detected_text = recognizer.recognize_google(audio_data)
                logger.info(f"Successfully recognized text: {detected_text[:50]}...")
            except:
                # Fallback to Sphinx if Google fails (offline, but less accurate)
                try:
                    detected_text = recognizer.recognize_sphinx(audio_data)
                    logger.info("Used Sphinx fallback")
                except:
                    detected_text = None

            if not detected_text:
                return jsonify({"error": "Could not understand audio"}), 400

        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return jsonify({"error": "Could not understand audio. Please speak clearly."}), 400
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return jsonify({"error": "Speech recognition service unavailable"}), 503

        # Detect language of original text
        try:
            detected_lang = detect(detected_text)
            logger.info(f"Detected language: {detected_lang}")
        except:
            detected_lang = "unknown"
            logger.warning("Could not detect language")

        # Translation
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated_text = translator.translate(detected_text)
            logger.info(f"Translated text: {translated_text[:50]}...")
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return jsonify({"error": "Translation service unavailable"}), 503

        # Text to Speech
        try:
            tts = gTTS(text=translated_text, lang=target_lang, slow=False)
            speech_filename = os.path.join(
                app.config['TEMP_DIR'],
                f"speech_{unique_id}.mp3"
            )
            tts.save(speech_filename)
            temp_files.append(speech_filename)
            logger.debug(f"TTS audio saved to {speech_filename}")
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return jsonify({"error": "Text-to-speech conversion failed"}), 503

        # Clean up input audio files (keep the speech file for download)
        for file in [temp_webm, temp_wav]:
            try:
                if os.path.exists(file):
                    os.remove(file)
                    logger.debug(f"Cleaned up {file}")
            except Exception as e:
                logger.error(f"Cleanup error for {file}: {e}")

        # Success response
        return jsonify({
            "success": True,
            "detected_text": detected_text,
            "detected_lang": detected_lang,
            "translated_text": translated_text,
            "target_lang": target_lang,
            "audio_url": f"/audio/{os.path.basename(speech_filename)}"
        })

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        
        # Clean up any temporary files on error
        for file in temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except:
                pass
        
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------------
# Serve Audio File
# -----------------------------------
@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """
    Serve the generated audio file and delete it after sending
    """
    file_path = os.path.join(app.config['TEMP_DIR'], filename)
    
    # Security: Prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Attempted directory traversal: {filename}")
        return jsonify({"error": "Invalid filename"}), 400
    
    if not os.path.exists(file_path):
        logger.warning(f"Audio file not found: {filename}")
        return jsonify({"error": "Audio file not found or expired"}), 404
    
    try:
        # Send file and delete after sending
        response = send_file(
            file_path,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=f"translated_speech.mp3"
        )
        
        # Delete file after sending
        @response.call_on_close
        def cleanup():
            try:
                # Wait a moment to ensure file is sent
                time.sleep(1)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted audio file: {filename}")
            except Exception as e:
                logger.error(f"Error deleting audio file {filename}: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {e}")
        return jsonify({"error": "Error serving audio file"}), 500

# -----------------------------------
# Get supported languages
# -----------------------------------
@app.route('/languages', methods=['GET'])
def get_languages():
    """Return list of supported languages"""
    return jsonify({
        "supported_languages": SUPPORTED_LANGUAGES
    })

# -----------------------------------
# Manual cleanup endpoint (admin only - add authentication in production)
# -----------------------------------
@app.route('/cleanup', methods=['POST'])
def manual_cleanup():
    """Manually trigger cleanup of old files"""
    try:
        cleanup_old_files()
        return jsonify({"success": True, "message": "Cleanup completed"})
    except Exception as e:
        logger.error(f"Manual cleanup error: {e}")
        return jsonify({"error": "Cleanup failed"}), 500

# -----------------------------------
# Run Server
# -----------------------------------
if __name__ == '__main__':
    # In production, use a production WSGI server like gunicorn
    # and set debug=False
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,  # Set to False in production
        threaded=True  # Enable threading for concurrent requests
    )