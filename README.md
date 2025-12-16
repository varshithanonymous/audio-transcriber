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

### B. Intelligent Vocabulary Generation
**Multi-API Vocabulary Bank System** - Generates truly unique words based on your existing vocabulary:

#### APIs Used for Word Generation:
1. **Datamuse API** (Primary English word generation):
   - `ml` parameter: Words with similar meaning
   - `rel_rhy` parameter: Rhyming words
   - `sl` parameter: Sound-alike words
   - `topics` parameter: Topic-based vocabulary (education, technology, nature, science, art, music, sports, food)
   - `lc` parameter: Words that frequently appear together

2. **Dictionary API** (English synonyms/antonyms):
   - Extracts synonyms and antonyms from word definitions
   - URL: `https://api.dictionaryapi.dev/api/v2/entries/en/{word}`

3. **MyMemory Translation API** (Spanish/Hindi generation):
   - Translates base words: Source language → English → Target language
   - Generates related words through English intermediary
   - URL: `https://api.mymemory.translated.net/get?q={word}&langpair={source}|{target}`

#### Generation Process:
- **English**: Direct API calls to Datamuse for semantic relationships
- **Spanish**: Base word → English → Datamuse related words → Spanish
- **Hindi**: Base word → English → Datamuse related words → Hindi
- **Uniqueness**: Excludes ALL existing words from transcripts, validated words, vocabulary bank, and learning databases
- **Storage**: Saves generated words to local SQLite database with language detection

### C. Adaptive Learning & Tutoring
1. Interactive learning interface with questions and answers
2. Audio-first input with text fallback
3. Incremental learning: adjusts difficulty based on performance
4. Personalized lessons and daily challenges
5. **Tutor Controls**: Complete data management with fresh start options

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

## Multi-Language Support

### Word Validation
The system supports word validation for all three languages:
- **English**: Full dictionary definitions via Dictionary API
- **Spanish**: Translations and meanings via WordReference and MyMemory APIs
- **Hindi**: Translations to English with meanings via MyMemory API

Validation responses are automatically returned **in the detected language**:
- English: "✓ Valid word: [word]. [definition]"
- Spanish: "✓ Palabra válida: [word]. [meaning]"
- Hindi: "✓ वैध शब्द: [word]. [meaning]"

### Vocabulary Generation APIs
**English Words**:
- **Datamuse API**: `https://api.datamuse.com/words?ml={word}` (similar meaning)
- **Datamuse API**: `https://api.datamuse.com/words?rel_rhy={word}` (rhyming)
- **Datamuse API**: `https://api.datamuse.com/words?sl={word}` (sound-alike)
- **Datamuse API**: `https://api.datamuse.com/words?topics={topic}` (topic-based)
- **Dictionary API**: `https://api.dictionaryapi.dev/api/v2/entries/en/{word}` (synonyms/antonyms)

**Spanish Words**:
- **MyMemory Translation**: `https://api.mymemory.translated.net/get?q={word}&langpair=es|en`
- **Datamuse API**: English related words generation
- **MyMemory Translation**: `https://api.mymemory.translated.net/get?q={word}&langpair=en|es`

**Hindi Words**:
- **MyMemory Translation**: `https://api.mymemory.translated.net/get?q={word}&langpair=hi|en`
- **Datamuse API**: English related words generation
- **MyMemory Translation**: `https://api.mymemory.translated.net/get?q={word}&langpair=en|hi`

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

### Core Features
- `GET /` - Main menu
- `GET /transcription` - Real-time transcription page
- `GET /validation_page` - Word validation interface
- `GET /tutor` - Adaptive tutor with vocabulary generation
- `GET /validate_word?word=<word>&lang=<lang>` - Validate a word
- `GET /data?lang=<lang>` - Get transcription history
- `POST /record/start` - Start recording
- `POST /record/stop` - Stop recording

### Vocabulary Generation
- `GET /api/vocabulary_bank` - Generate unique words using multiple APIs
- `GET /api/get_stored_vocab_bank` - Get stored vocabulary bank
- `POST /api/clear_vocab_bank` - Clear vocabulary bank

### Tutor Controls
- `POST /api/clear_tutor_all` - Clear all tutor data (fresh start)
- `POST /api/clear_tutor_new_words` - Clear user vocabulary only
- `POST /api/clear_tutor_oov` - Clear OOV words only
- `POST /api/clear_all_data` - Complete system reset

## Notes

- Audio files are saved locally in `audio_clips/` directory
- All transcriptions are stored in SQLite database
- Word validation requires internet connection
- Speech recognition works offline using Vosk models
- **Vocabulary generation requires internet** for API access to Datamuse and MyMemory
- Generated vocabulary is stored locally and persists across sessions
- System ensures **100% unique words** by checking all existing databases before generation
