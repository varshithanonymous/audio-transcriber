# Audio Transcriber - Multi-Language Speech Recognition

A real-time audio transcription system supporting **English, Spanish, and Hindi** with offline capabilities and online word validation.

## Features

### A. Audio Transcription & Validation
1. **Offline Speech Recognition**: Listen to audio and capture spoken words in a local database using Vosk models (works without internet)
   - English model (~40 MB)
   - Spanish model
   - Hindi model
2. **Audio Capture**: Records audio in configurable time blocks (5 seconds, 30 seconds, or 1 minute)
3. **Multi-Language Word Validation**: When internet is available, validates words in **English, Spanish, and Hindi**:
   - **English**: Uses Dictionary API for definitions
   - **Spanish**: Uses WordReference API and MyMemory Translation API
   - **Hindi**: Uses MyMemory Translation API with English translation
   - Responses are returned **in the detected language**
4. **Local Dictionary**: Stores validated words with meanings in local SQLite database
### B. Adaptive Learning & Tutoring
1. Interactive learning interface with questions and answers
2. Audio-first input with text fallback
3. Incremental learning: adjusts difficulty based on performance
4. Personalized lessons and daily challenges

## Installation

### Prerequisites
- Python 3.7+
- Microphone access
- Internet connection (for word validation)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/varshithanonymous/audio-transcriber.git
   cd audio-transcriber
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download Vosk Models**
   
   The app requires Vosk speech recognition models for each language. Download them from [Vosk Models](https://alphacephei.com/vosk/models):
   
   - **English (small)**: ~40 MB - Recommended for offline use
   - **Spanish**: Download Spanish model
   - **Hindi**: Download Hindi model
   
   Extract each model into the `models/` directory:
   ```
   models/
   ├── en/     (English model files)
   ├── es/     (Spanish model files)
   └── hi/     (Hindi model files)
   ```
   
   Or use the provided script:
   ```bash
   python download_models.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the web interface**
   - Open browser to: `http://localhost:5001`
   - Navigate to "Real-Time Transcription" to start recording
   - Use "Word Validation" to validate words in any supported language

## Multi-Language Validation

The system now supports word validation for all three languages:

- **English**: Full dictionary definitions via Dictionary API
- **Spanish**: Translations and meanings via WordReference and MyMemory APIs
- **Hindi**: Translations to English with meanings via MyMemory API

Validation responses are automatically returned **in the detected language**:
- English: "✓ Valid word: [word]. [definition]"
- Spanish: "✓ Palabra válida: [word]. [meaning]"
- Hindi: "✓ वैध शब्द: [word]. [meaning]"

## Project Structure

```
audio-transcriber/
├── app.py                 # Flask web server and API routes
├── transcriber.py         # Background audio transcription
├── adaptive_chatbot.py    # Learning and vocabulary tracking
├── templates/             # HTML templates
│   ├── main_menu.html
│   ├── transcription.html
│   ├── validation.html
│   ├── dashboard.html
│   └── ...
├── models/                # Vosk speech recognition models (download separately)
├── audio_clips/           # Saved audio recordings
├── transcriptions.db      # SQLite database for transcripts
└── word_database.db       # SQLite database for validated words
```

## API Endpoints

- `GET /` - Main menu
- `GET /transcription` - Real-time transcription page
- `GET /validation_page` - Word validation interface
- `GET /validate_word?word=<word>&lang=<lang>` - Validate a word
- `GET /data?lang=<lang>` - Get transcription history
- `POST /record/start` - Start recording
- `POST /record/stop` - Stop recording

## Notes

- Audio files are saved locally in `audio_clips/` directory
- All transcriptions are stored in SQLite database
- Word validation requires internet connection
- Speech recognition works offline using Vosk models
