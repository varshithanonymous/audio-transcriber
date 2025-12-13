import os, queue, json, sqlite3, time, threading, wave
try:
    import sounddevice as sd
except ImportError:
    print("Warning: sounddevice not available, audio recording disabled")
    sd = None
import vosk
from adaptive_chatbot import AdaptiveChatbot

# Paths to models
MODEL_PATHS = {
    "en": "models/en",
    "es": "models/es",
    "hi": "models/hi"
}

recognizers = {}
print("Loading Vosk models...", flush=True)
for lang, path in MODEL_PATHS.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model directory not found for {lang}: {path}\nDownload model from: https://alphacephei.com/vosk/models")
    try:
        print(f"  Loading {lang.upper()} model from {path}...", flush=True)
        model = vosk.Model(path)
        recognizers[lang] = vosk.KaldiRecognizer(model, 16000)
        print(f"  ✓ {lang.upper()} model loaded successfully", flush=True)
    except Exception as e:
        raise RuntimeError(f"Failed to load {lang} model from {path}: {e}\nMake sure the model files are properly extracted.")
print(f"✓ All {len(recognizers)} models loaded successfully!", flush=True)

DB_FILE = "transcriptions.db"
AUDIO_DIR = "audio_clips"
os.makedirs(AUDIO_DIR, exist_ok=True)

q = queue.Queue()
stop_event = threading.Event()
listener_thread = None

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            language TEXT,
            text TEXT,
            audio_file TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()
chatbot = AdaptiveChatbot()
is_listening = False

# Enhanced features
def detect_language_offline(text):
    if not text.strip(): return 'unknown'
    en_words = {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with'}
    es_words = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se'}
    words = text.lower().split()
    en_score = sum(1 for word in words if word in en_words)
    es_score = sum(1 for word in words if word in es_words)
    if en_score > es_score and en_score > 0: return 'en'
    elif es_score > 0: return 'es'
    return 'unknown'

def validate_word_online(user_id, word, language):
    try:
        import requests
        import urllib.parse
        
        # English: Use dictionary API
        if language == 'en':
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    meanings = data[0].get('meanings', [])
                    if meanings:
                        meaning = meanings[0].get('definitions', [{}])[0].get('definition', '')
                        # Store in database
                        conn_word = sqlite3.connect("word_database.db")
                        conn_word.execute("CREATE TABLE IF NOT EXISTS validated_words (user_id TEXT, word TEXT, language TEXT, meaning TEXT, timestamp TEXT)")
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        conn_word.execute("INSERT INTO validated_words VALUES (?, ?, ?, ?, ?)", (user_id, word.lower(), language, meaning, timestamp))
                        conn_word.commit()
                        conn_word.close()
                        return meaning
        
        # Spanish: Use translation API
        elif language == 'es':
            try:
                # Try WordReference API
                word_encoded = urllib.parse.quote(word)
                url = f"https://api.wordreference.com/0.8/json/esen/{word_encoded}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if 'term0' in data:
                        term = data.get('term0', {})
                        entries = term.get('PrincipalTranslations', {})
                        if entries:
                            first_entry = list(entries.values())[0] if entries else None
                            if first_entry and 'OriginalTerm' in first_entry:
                                meaning = first_entry.get('OriginalTerm', {}).get('term', '')
                                if meaning:
                                    conn_word = sqlite3.connect("word_database.db")
                                    conn_word.execute("CREATE TABLE IF NOT EXISTS validated_words (user_id TEXT, word TEXT, language TEXT, meaning TEXT, timestamp TEXT)")
                                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                                    conn_word.execute("INSERT INTO validated_words VALUES (?, ?, ?, ?, ?)", (user_id, word.lower(), language, f"Español: {meaning}", timestamp))
                                    conn_word.commit()
                                    conn_word.close()
                                    return f"Español: {meaning}"
            except:
                pass
            
            # Fallback: MyMemory Translation
            try:
                url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(word)}&langpair=es|en"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('responseStatus') == 200:
                        translated = data.get('responseData', {}).get('translatedText', '')
                        if translated and translated.lower() != word.lower():
                            conn_word = sqlite3.connect("word_database.db")
                            conn_word.execute("CREATE TABLE IF NOT EXISTS validated_words (user_id TEXT, word TEXT, language TEXT, meaning TEXT, timestamp TEXT)")
                            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                            conn_word.execute("INSERT INTO validated_words VALUES (?, ?, ?, ?, ?)", (user_id, word.lower(), language, f"Español: {word} → {translated}", timestamp))
                            conn_word.commit()
                            conn_word.close()
                            return f"Español: {word} → {translated}"
            except:
                pass
        
        # Hindi: Use translation API
        elif language == 'hi':
            try:
                url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(word)}&langpair=hi|en"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('responseStatus') == 200:
                        translated = data.get('responseData', {}).get('translatedText', '')
                        if translated and translated.lower() != word.lower():
                            conn_word = sqlite3.connect("word_database.db")
                            conn_word.execute("CREATE TABLE IF NOT EXISTS validated_words (user_id TEXT, word TEXT, language TEXT, meaning TEXT, timestamp TEXT)")
                            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                            conn_word.execute("INSERT INTO validated_words VALUES (?, ?, ?, ?, ?)", (user_id, word.lower(), language, f"हिंदी: {word} → {translated}", timestamp))
                            conn_word.commit()
                            conn_word.close()
                            return f"हिंदी: {word} → {translated}"
            except:
                pass
    except Exception as e:
        print(f"Validation error: {e}", flush=True)
    return None

def save_transcript(text, lang, audio_path=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO transcripts (timestamp, language, text, audio_file) VALUES (?, ?, ?, ?)",
        (ts, lang, text, audio_path)
    )
    conn.commit()
    
    # Validate words in background
    words = text.lower().split()
    for word in words:
        if word.isalpha() and len(word) > 2:
            threading.Thread(target=validate_word_online, args=("default_user", word, lang), daemon=True).start()

    # Feed transcript into adaptive chatbot for vocabulary growth/OOV tracking
    try:
        chatbot.process_spoken_words("default_user", text, lang)
    except Exception as e:
        # Keep transcription robust even if learning layer has an issue
        print(f"[Chatbot] failed to process words: {e}", flush=True)

def save_audio_chunk(raw_data, lang):
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{lang}_{ts}.wav"
    filepath = os.path.join(AUDIO_DIR, filename)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(raw_data)
    return filepath

def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status, flush=True)
    q.put(bytes(indata))

def transcribe_loop():
    global is_listening
    if sd is None:
        print("Audio recording not available")
        is_listening = False
        return

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000,
                               dtype="int16", channels=1,
                               callback=audio_callback):
            print("🎤 Listening... (EN, ES, HI + offline detection + validation)")
            is_listening = True
            while not stop_event.is_set():
                data = q.get()
                if stop_event.is_set():
                    break
                if not data:
                    continue
                for lang, rec in recognizers.items():
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip()
                        if text:
                            detected_lang = detect_language_offline(text)
                            final_lang = detected_lang if detected_lang != 'unknown' else lang

                            audio_path = save_audio_chunk(data, final_lang)
                            print(f"[{final_lang.upper()}] {text}  🎵 saved {audio_path}")
                            save_transcript(text, final_lang, audio_path)
    except Exception as e:
        print(f"Audio error: {e}")
    finally:
        is_listening = False

def start_transcriber():
    global listener_thread
    if listener_thread and listener_thread.is_alive():
        return
    stop_event.clear()
    listener_thread = threading.Thread(target=transcribe_loop, daemon=True)
    listener_thread.start()

def stop_transcriber():
    stop_event.set()
    q.put(b"")  # unblock queue
