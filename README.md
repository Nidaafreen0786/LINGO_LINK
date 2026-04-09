# LingoLink Backend
**LingoLink** is an AI-powered multilingual communication assistant that enables users to translate, transcribe, and communicate across languages in real time. This repository contains the Flask-based backend API that powers voice translation and speech recognition for the LingoLink extension and web application.
## Overview
LingoLink Backend provides a RESTful API for speech-to-text conversion using OpenAI Whisper, language detection and translation using Deep Translator, text-to-speech synthesis using gTTS, and cross-origin resource sharing for seamless communication with browser extensions or web clients. The backend is designed to be lightweight, easily deployable, and optimized for Hugging Face Spaces or Render.
## Project Structure
LingoLink/
└── backend/
    ├── app.py                 # Main Flask application
    ├── requirements.txt       # Python dependencies
    ├── runtime.txt            # Python version for deployment
    ├── extension/             # Chrome extension frontend
    │   ├── popup.html
    │   ├── popup.js
    │   ├── style.css
    │   └── manifest.json
    ├── uploads/               # Temporary audio files (ignored in .gitignore)
    ├── .gitignore
    └── README.md
## Technology Stack
Backend Framework: Flask (Python 3.13)  
Speech Recognition: OpenAI Whisper / SpeechRecognition  
Translation: Deep Translator  
Text-to-Speech: gTTS  
Server: Gunicorn  
Deployment: Hugging Face Spaces / Render
## Installation and Local Setup
1. Clone the repository  
   git clone https://github.com/Nidaafreen0786/LINGO_LINK.git  
   cd LINGOLINK  
2. Create and activate a virtual environment  
   python -m venv .venv  
   .venv\Scripts\activate      # Windows  
   source .venv/bin/activate   # Mac/Linux  
3. Install dependencies  
   pip install -r requirements.txt  
4. Run the Flask application  
   python app.py  
5. Access the API at http://127.0.0.1:5000  
## Deployment (Hugging Face Spaces)
1. Push this repository to GitHub.  
2. Create a new Space on Hugging Face Spaces.  
3. Choose: SDK: Other, Repository: LingoLink-backend.  
4. The Space will automatically install dependencies from `requirements.txt` and start the Flask server with:  
   gunicorn app:app  
## Requirements
Flask==3.0.3  
Flask-Cors==4.0.0  
SpeechRecognition==3.10.0  
pydub==0.25.1  
deep-translator==1.11.4  
langdetect==1.0.9  
ffmpeg-python==0.2.0  
gTTS==2.5.3  
openai-whisper  
gunicorn==21.2.0  
## Chrome Extension Integration
The `extension/` directory contains the Chrome Extension frontend files that interact with this backend. These include the popup interface, JavaScript logic, and styling required to capture audio input and communicate with the Flask API.
## Author
**Nida Afreen**  
Focused on AI-driven communication systems and natural language technologies.  
GitHub: [https://github.com/Nidaafreen0786](https://github.com/Nidaafreen0786/LINGO_LINK.git)
