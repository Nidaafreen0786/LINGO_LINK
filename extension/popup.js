let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let serverAvailable = false;

// Check if server is running
async function checkServer() {
    try {
        const response = await fetch('http://127.0.0.1:5000/health');
        if (response.ok) {
            serverAvailable = true;
            updateStatus('Server connected ✓', 'success');
        }
    } catch (error) {
        serverAvailable = false;
        updateStatus('⚠️ Server not running. Start the Python server first.', 'error');
    }
}

// Update status message
function updateStatus(message, type = 'info') {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = type;
}

// Initialize when popup opens
document.addEventListener('DOMContentLoaded', () => {
    checkServer();
    setupRecording();
});

function setupRecording() {
    const recordBtn = document.getElementById('recordBtn');
    
    recordBtn.addEventListener('click', async () => {
        if (!serverAvailable) {
            updateStatus('❌ Please start the Python server first', 'error');
            return;
        }
        
        if (!isRecording) {
            await startRecording();
        } else {
            stopRecording();
        }
    });
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            processAudio(audioBlob);
            
            // Stop all audio tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        document.getElementById('recordBtn').textContent = '⏹️ Stop Recording';
        document.getElementById('recordBtn').classList.add('recording');
        updateStatus('🔴 Recording... Click Stop when done', 'recording');
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        updateStatus('❌ Microphone access denied', 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById('recordBtn').textContent = '🎤 Start Recording';
        document.getElementById('recordBtn').classList.remove('recording');
        updateStatus('⏳ Processing audio...', 'processing');
    }
}

async function processAudio(audioBlob) {
    try {
        const targetLang = document.getElementById('targetLang').value;
        
        // Create form data
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('target_lang', targetLang);
        
        // Send to server
        const response = await fetch('http://127.0.0.1:5000/process-audio', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Update UI with results
            document.getElementById('detectedText').textContent = data.detected_text;
            document.getElementById('translatedText').textContent = data.translated_text;
            
            // Play the translated audio
            if (data.audio_url) {
                const audioUrl = `http://127.0.0.1:5000${data.audio_url}`;
                const audioPlayer = document.getElementById('audioPlayer');
                audioPlayer.src = audioUrl;
                audioPlayer.style.display = 'block';
                audioPlayer.play();
            }
            
            updateStatus('✅ Processing complete!', 'success');
        } else {
            throw new Error(data.error || 'Unknown error');
        }
        
    } catch (error) {
        console.error('Error processing audio:', error);
        document.getElementById('detectedText').textContent = '—';
        document.getElementById('translatedText').textContent = '—';
        updateStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Periodically check server status
setInterval(checkServer, 5000);