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
        print(f"  [OK] {lang.upper()} model loaded successfully", flush=True)
    except Exception as e:
        raise RuntimeError(f"Failed to load {lang} model from {path}: {e}\nMake sure the model files are properly extracted.")
print(f"[OK] All {len(recognizers)} models loaded successfully!", flush=True)

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
    
    # Character sets
    hi_chars = set('अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञ')
    
    # Common words
    en_words = {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with', 'i', 'you'}
    es_words = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'por', 'con'}
    
    words = text.lower().split()
    
    # Check for Hindi script usage
    hi_char_count = sum(1 for char in text if char in hi_chars)
    if hi_char_count > 0:
        return 'hi'
        
    # Check word overlap
    en_score = sum(1 for word in words if word in en_words)
    es_score = sum(1 for word in words if word in es_words)
    
    if en_score > es_score and en_score > 0: return 'en'
    elif es_score > en_score and es_score > 0: return 'es'
    
    return 'unknown'

def validate_word_online(user_id, word, language):
    # Local fallback dictionary for offline/basic validation
    offline_dict = {
        'en': {
            'hello': 'A greeting', 'world': 'The earth or universe', 'time': 'Indefinite continued progress of existence',
            'person': 'A human being', 'year': '365 days', 'way': 'A method, style, or manner', 'day': '24 hours',
            'thing': 'An object', 'man': 'An adult male human', 'life': 'The existence of an individual',
            'hand': 'End part of the arm', 'part': 'Amount or section', 'child': 'A young human',
            'eye': 'Organ of sight', 'woman': 'An adult female human', 'place': 'A particular position or point',
            'work': 'Activity involving mental or physical effort', 'week': 'Period of seven days',
            'case': 'Instance of a particular situation', 'point': 'A dot or small mark',
            'government': 'The governing body of a nation', 'company': 'A commercial business',
            'number': 'An arithmetical value', 'group': 'A number of people or things',
            'problem': 'A matter or situation regarded as unwelcome', 'fact': 'A thing that is known or proved to be true'
        },
        'es': {
            'hola': 'English: Hello', 'mundo': 'English: World', 'tiempo': 'English: Time',
            'persona': 'English: Person', 'año': 'English: Year', 'camino': 'English: Way',
            'día': 'English: Day', 'cosa': 'English: Thing', 'hombre': 'English: Man',
            'vida': 'English: Life', 'mano': 'English: Hand', 'parte': 'English: Part',
            'niño': 'English: Child', 'ojo': 'English: Eye', 'mujer': 'English: Woman',
            'lugar': 'English: Place', 'trabajo': 'English: Work', 'semana': 'English: Week',
            'caso': 'English: Case', 'punto': 'English: Point', 'gobierno': 'English: Government',
            'empresa': 'English: Company', 'número': 'English: Number', 'grupo': 'English: Group',
            'problema': 'English: Problem', 'hecho': 'English: Fact'
        },
        'hi': {
            'नमस्ते': 'English: Hello', 'दुनिया': 'English: World', 'समय': 'English: Time',
            'व्यक्ति': 'English: Person', 'साल': 'English: Year', 'रास्ता': 'English: Way',
            'दिन': 'English: Day', 'चीज': 'English: Thing', 'आदमी': 'English: Man',
            'जीवन': 'English: Life', 'हाथ': 'English: Hand', 'भाग': 'English: Part',
            'बच्चा': 'English: Child', 'आंख': 'English: Eye', 'महिला': 'English: Woman',
            'जगह': 'English: Place', 'काम': 'English: Work', 'सप्ताह': 'English: Week',
            'मामला': 'English: Case', 'बिंदु': 'English: Point', 'सरकार': 'English: Government',
            'कंपनी': 'English: Company', 'संख्या': 'English: Number', 'समूह': 'English: Group',
            'समस्या': 'English: Problem', 'तथ्य': 'English: Fact'
        }
    }

    # Use a new table for validation history that allows duplicates
    conn_word = sqlite3.connect("word_database.db")
    conn_word.execute("""
        CREATE TABLE IF NOT EXISTS validation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id TEXT, 
            word TEXT, 
            language TEXT, 
            meaning TEXT, 
            status TEXT, 
            timestamp TEXT
        )
    """)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Check offline dict FIRST
    meaning = offline_dict.get(language, {}).get(word.lower())
    status = "valid" if meaning else "pending"
    
    # Insert initial record
    cursor = conn_word.cursor()
    cursor.execute(
        "INSERT INTO validation_log (user_id, word, language, meaning, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
        (user_id, word.lower(), language, meaning if meaning else "", status, timestamp)
    )
    log_id = cursor.lastrowid
    conn_word.commit()
    conn_word.close()

    if status == "valid":
        return meaning

    # If not in offline dict, try online
    try:
        import requests
        import urllib.parse
        
        # English: Use dictionary API
        if language == 'en':
            try:
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        meanings = data[0].get('meanings', [])
                        if meanings:
                            meaning = meanings[0].get('definitions', [{}])[0].get('definition', '')
                            status = "valid"
                elif response.status_code == 404:
                    status = "invalid" # Explicitly not found
            except requests.exceptions.RequestException:
                status = "pending" # Network issue, try later
        
        # Spanish: Use translation API
        elif language == 'es':
            try:
                # Try WordReference API first
                word_encoded = urllib.parse.quote(word)
                url = f"https://api.wordreference.com/0.8/json/esen/{word_encoded}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if 'term0' in data:
                        term = data.get('term0', {})
                        entries = term.get('PrincipalTranslations', {})
                        if entries:
                            first = list(entries.values())[0]
                            if 'OriginalTerm' in first:
                                meaning = f"Español: {first['OriginalTerm']['term']}"
                                status = "valid"
            except: pass
            
            if not meaning:
                try:
                    url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(word)}&langpair=es|en"
                    response = requests.get(url, timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('responseStatus') == 200:
                            trans = data['responseData']['translatedText']
                            if trans and trans.lower() != word.lower():
                                meaning = f"Español: {word} → {trans}"
                                status = "valid"
                        elif data.get('responseStatus') in [404, 429]: # Not found or limit
                             if data.get('responseStatus') == 404: status = "invalid"
                             else: status = "pending"
                except requests.exceptions.RequestException:
                    status = "pending"
        
        # Hindi: Use translation API
        elif language == 'hi':
            try:
                url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(word)}&langpair=hi|en"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('responseStatus') == 200:
                        trans = data['responseData']['translatedText']
                        if trans and trans.lower() != word.lower():
                            meaning = f"हिंदी: {word} → {trans}"
                            status = "valid"
                    elif data.get('responseStatus') == 404:
                         status = "invalid"
            except Exception:
                status = "pending"

        # Update the log entry
        conn_word = sqlite3.connect("word_database.db")
        conn_word.execute(
            "UPDATE validation_log SET meaning=?, status=? WHERE id=?", 
            (meaning if meaning else ("Waiting for connection..." if status == 'pending' else "Not found"), status, log_id)
        )
        conn_word.commit()
        conn_word.close()
        
        return meaning

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
    
    # Remove punctuation
    import string
    translator = str.maketrans('', '', string.punctuation + '।')
    clean_text = text.translate(translator)
    
    # Validate words in background
    words = clean_text.lower().split()
    for word in words:
        # Check length (allow shorter words for Hindi as characters are complex)
        min_len = 1 if lang == 'hi' else 2
        if len(word) > min_len:
            # Simple check: isalpha works for unicode, but we might want to be inclusive
            if word.isalpha() or lang == 'hi':
                threading.Thread(target=validate_word_online, args=("default_user", word, lang), daemon=True).start()

    # Feed transcript into adaptive chatbot for vocabulary growth/OOV tracking
    try:
        chatbot.process_spoken_words("default_user", text, lang)
    except Exception as e:
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
            print("[MIC] Listening... (EN, ES, HI + offline detection + validation)")
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
                            # Validation Step: Ensure the output matches the language model
                            is_valid = False
                            
                            # Hindi model must produce Hindi characters
                            if lang == 'hi':
                                if any(c in text for c in 'अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञ'):
                                    is_valid = True
                            
                            # English/Spanish check (basic ASCII check + common words)
                            elif lang in ['en', 'es']:
                                # If pure ASCII and not empty, it's likely okay for EN/ES models
                                # But we can be stricter: reject if it looks like the OTHER language
                                detected = detect_language_offline(text)
                                if detected == 'unknown' or detected == lang:
                                    is_valid = True
                                elif detected != lang:
                                    # Logic detection says it's Spanish but we are in English model -> suspicious, but possible (borrowed words)
                                    # Let's trust model if confidence is high, but Vosk doesn't give confidence easily here.
                                    # Stricter: ignore cross-matches
                                    is_valid = False

                            if is_valid:
                                detected_lang = detect_language_offline(text)
                                final_lang = detected_lang if detected_lang != 'unknown' else lang
    
                                audio_path = save_audio_chunk(data, final_lang)
                                print(f"[{final_lang.upper()}] {text}  [AUDIO] saved {audio_path}")
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
