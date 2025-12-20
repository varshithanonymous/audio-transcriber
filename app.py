from flask import Flask, render_template, jsonify, Response, send_from_directory, request, redirect
import sqlite3
import csv
import io
import os
import transcriber
from adaptive_chatbot import AdaptiveChatbot
import threading
import time
import random
import json

# Enhanced features
class OfflineLanguageDetector:
    def __init__(self):
        self.patterns = {
            'en': {'chars': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'common_words': {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with'}},
            'es': {'chars': set('abcdefghijklmnopqrstuvwxyzáéíóúüñABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), 'common_words': {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se'}},
            'hi': {'chars': set('अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञ'), 'common_words': {'है', 'का', 'की', 'के', 'में', 'से', 'को', 'और', 'यह', 'वह'}}
        }
    def detect_language(self, text):
        if not text.strip(): return 'unknown'
        scores = {'en': 0, 'es': 0, 'hi': 0}
        words = text.lower().split()
        for lang, data in self.patterns.items():
            char_score = sum(1 for char in text if char in data['chars'])
            scores[lang] += char_score / len(text) * 50
            word_score = sum(1 for word in words if word in data['common_words'])
            scores[lang] += word_score / len(words) * 50 if words else 0
        detected = max(scores, key=scores.get)
        return detected if scores[detected] > 10 else 'unknown'

class WordValidator:
    def __init__(self, db_file="word_database.db"):
        self.db_file = db_file
        self.init_db()
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        conn.execute("CREATE TABLE IF NOT EXISTS validated_words (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, word TEXT, language TEXT, meaning TEXT, is_valid INTEGER, timestamp TEXT, UNIQUE(user_id, word, language))")
        conn.commit()
        conn.close()
    def is_online(self):
        try:
            import requests
            requests.get("https://httpbin.org/status/200", timeout=3)
            return True
        except: return False
    def get_word_meaning(self, word, language):
        if not self.is_online(): return None
        try:
            import requests
            import urllib.parse
            
            # English: Use dictionary API
            if language == 'en':
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        meanings = data[0].get('meanings', [])
                        if meanings: 
                            definition = meanings[0].get('definitions', [{}])[0].get('definition', '')
                            return f"English: {definition}"
            
            # Spanish: Use MyMemory Translation API + WordReference
            elif language == 'es':
                # Try WordReference API first (free, no key needed)
                try:
                    word_encoded = urllib.parse.quote(word)
                    url = f"https://api.wordreference.com/0.8/json/esen/{word_encoded}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if 'term0' in data:
                            # Extract first translation
                            term = data.get('term0', {})
                            entries = term.get('PrincipalTranslations', {})
                            if entries:
                                first_entry = list(entries.values())[0] if entries else None
                                if first_entry and 'OriginalTerm' in first_entry:
                                    meaning = first_entry.get('OriginalTerm', {}).get('term', '')
                                    if meaning:
                                        return f"Español: {meaning}"
                except:
                    pass
                
                # Fallback: Use MyMemory Translation API
                try:
                    url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(word)}&langpair=es|en"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('responseStatus') == 200:
                            translated = data.get('responseData', {}).get('translatedText', '')
                            if translated and translated.lower() != word.lower():
                                # Get English meaning of translated word
                                en_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(translated)}"
                                en_resp = requests.get(en_url, timeout=5)
                                if en_resp.status_code == 200:
                                    en_data = en_resp.json()
                                    if en_data and len(en_data) > 0:
                                        meanings = en_data[0].get('meanings', [])
                                        if meanings:
                                            definition = meanings[0].get('definitions', [{}])[0].get('definition', '')
                                            return f"Español: {word} → English: {translated} ({definition})"
                                return f"Español: {word} → English: {translated}"
                except:
                    pass
            
            # Hindi: Use translation API
            elif language == 'hi':
                try:
                    # Use MyMemory Translation API to translate Hindi to English
                    url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(word)}&langpair=hi|en"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('responseStatus') == 200:
                            translated = data.get('responseData', {}).get('translatedText', '')
                            if translated and translated.lower() != word.lower():
                                # Get English meaning of translated word
                                en_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(translated)}"
                                en_resp = requests.get(en_url, timeout=5)
                                if en_resp.status_code == 200:
                                    en_data = en_resp.json()
                                    if en_data and len(en_data) > 0:
                                        meanings = en_data[0].get('meanings', [])
                                        if meanings:
                                            definition = meanings[0].get('definitions', [{}])[0].get('definition', '')
                                            return f"हिंदी: {word} → English: {translated} ({definition})"
                                return f"हिंदी: {word} → English: {translated}"
                except:
                    pass
            
            return None
        except Exception as e:
            print(f"Validation error: {e}")
            return None
    def validate_and_store_word(self, user_id, word, language):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT meaning, is_valid FROM validated_words WHERE user_id=? AND word=? AND language=?", (user_id, word.lower(), language))
        result = cursor.fetchone()
        if result:
            conn.close()
            meaning = result[0]
            is_valid = bool(result[1])
            # Return response in the detected language
            response_msg = self._get_validation_message(language, word, meaning, is_valid, True)
            return {'cached': True, 'meaning': meaning, 'is_valid': is_valid, 'message': response_msg}
        meaning = self.get_word_meaning(word, language)
        is_valid = meaning is not None
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR REPLACE INTO validated_words (user_id, word, language, meaning, is_valid, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (user_id, word.lower(), language, meaning or '', int(is_valid), timestamp))
        conn.commit()
        conn.close()
        response_msg = self._get_validation_message(language, word, meaning, is_valid, False)
        return {'cached': False, 'meaning': meaning, 'is_valid': is_valid, 'message': response_msg}
    
    def _get_validation_message(self, language, word, meaning, is_valid, cached):
        """Return validation message in the detected language"""
        if language == 'en':
            if is_valid:
                return f"✓ Valid word: {word}. {meaning}" if meaning else f"✓ Valid word: {word}"
            else:
                return f"✗ Word '{word}' not found in dictionary"
        elif language == 'es':
            if is_valid:
                return f"✓ Palabra válida: {word}. {meaning}" if meaning else f"✓ Palabra válida: {word}"
            else:
                return f"✗ La palabra '{word}' no se encontró en el diccionario"
        elif language == 'hi':
            if is_valid:
                return f"✓ वैध शब्द: {word}. {meaning}" if meaning else f"✓ वैध शब्द: {word}"
            else:
                return f"✗ शब्द '{word}' शब्दकोश में नहीं मिला"
        return f"Validation result: {word} - {'Valid' if is_valid else 'Invalid'}"
    def get_user_words(self, user_id, language=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        if language:
            cursor.execute("SELECT word, language, meaning, is_valid, timestamp FROM validated_words WHERE user_id=? AND language=? ORDER BY timestamp DESC", (user_id, language))
        else:
            cursor.execute("SELECT word, language, meaning, is_valid, timestamp FROM validated_words WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
        results = cursor.fetchall()
        conn.close()
        return [{'word': r[0], 'language': r[1], 'meaning': r[2], 'is_valid': bool(r[3]), 'timestamp': r[4]} for r in results]

app = Flask(__name__)
word_validator = WordValidator()
lang_detector = OfflineLanguageDetector()
chatbot = AdaptiveChatbot()

# Start background transcriber
transcriber.start_transcriber()

DB_FILE = "transcriptions.db"
AUDIO_DIR = "audio_clips"

def get_transcripts(limit=None, lang=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if lang and lang != "all":
        query = "SELECT timestamp, language, text, audio_file FROM transcripts WHERE language=? ORDER BY id DESC"
        params = (lang,)
    else:
        query = "SELECT timestamp, language, text, audio_file FROM transcripts ORDER BY id DESC"
        params = ()
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [{"timestamp": r[0], "language": r[1], "text": r[2], "audio_file": r[3]} for r in rows]

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/transcription")
def transcription_page():
    return render_template("transcription.html")

@app.route("/tutor")
def tutor_page():
    return render_template("tutor.html")

@app.route("/validation_page")
def validation_page():
    return render_template("validation.html")

@app.route("/language")
def language_page():
    return render_template("language_detection.html")

@app.route("/api/get_new_words")
def get_new_words():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM transcripts ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    
    all_words = set()
    for row in rows:
        words = row[0].lower().split()
        for word in words:
            clean_word = ''.join(c for c in word if c.isalpha())
            if len(clean_word) > 2:
                all_words.add(clean_word)
    
    validated_conn = sqlite3.connect("word_database.db")
    validated_cursor = validated_conn.cursor()
    
    # Store new words as pending validation (is_valid = -1) even in offline mode
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    for word in all_words:
        validated_cursor.execute("SELECT word FROM validated_words WHERE word=?", (word,))
        if not validated_cursor.fetchone():
            validated_cursor.execute(
                "INSERT OR IGNORE INTO validated_words (user_id, word, language, meaning, is_valid, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("default_user", word, "en", "", -1, timestamp)
            )
    
    validated_conn.commit()
    
    # Return words that need validation (is_valid = -1)
    validated_cursor.execute("SELECT word FROM validated_words WHERE is_valid = -1 ORDER BY timestamp DESC LIMIT 20")
    pending_words = [row[0] for row in validated_cursor.fetchall()]
    
    validated_conn.close()
    conn.close()
    return jsonify({"words": pending_words})

@app.route("/api/get_validation_log")
def get_validation_log():
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    # Check if table exists
    try:
        cursor.execute("SELECT * FROM validation_log ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        result = [
            {"id": r[0], "user_id": r[1], "word": r[2], "language": r[3], "meaning": r[4], "status": r[5], "timestamp": r[6]} 
            for r in rows
        ]
    except:
        result = []
    conn.close()
    return jsonify(result)

@app.route("/api/auto_generate_vocab")
def auto_generate_vocab():
    """Endpoint for context-aware continuous generation"""
    import random
    new_words = []
    
    # 1. Get the latest valid spoken word by the user to seed context
    conn_val = sqlite3.connect("word_database.db")
    seed_word = None
    seed_lang = 'en'
    try:
        cur = conn_val.cursor()
        cur.execute("SELECT word, language FROM validation_log WHERE status='valid' ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row: 
            seed_word = row[0].lower()
            seed_lang = row[1]
    except: pass
    conn_val.close()
    
    # Context Mapping (Simple localized graph)
    # If user says X, suggest Y, Z...
    context_map = {
        'money': ['bank', 'investment', 'cash', 'salary', 'profit'],
        'school': ['teacher', 'exam', 'book', 'student', 'class'],
        'time': ['clock', 'minute', 'hour', 'schedule', 'late'],
        'business': ['strategy', 'meeting', 'client', 'deal', 'market'],
        'travel': ['ticket', 'passport', 'airport', 'hotel', 'luggage'],
        
        # Spanish seeds
        'dinero': ['banco', 'inversión', 'efectivo', 'salario', 'ganancia'],
        
        # Hindi seeds
        'पैसा': ['बैंक', 'निवेश', 'नकद', 'वेतन', 'लाभ']
    }
    
    # Determine source based on seed
    source_pool = []
    source_context = "General"
    
    if seed_word:
        # Check direct match or partial match
        for key, val in context_map.items():
            if key in seed_word or seed_word in key:
                source_pool = val
                source_context = f"Because you said '{seed_word}'"
                break
    
    conn = sqlite3.connect("vocabulary_bank.db")
    
    # Extensive local dictionary fallback
    local_vocab = [
        ("Negotiation", "en", "Discussion aimed at reaching an agreement"),
        ("Strategy", "en", "A plan of action designed to achieve a long-term or overall aim"),
        ("Investment", "en", "The action or process of investing money for profit"),
        ("Innovation", "en", "A new method, idea, product, etc."),
        ("Deadline", "en", "The latest time or date by which something should be completed"),
        ("Collaboration", "en", "The action of working with someone to produce something"),
        ("Revenue", "en", "Income, especially when of a company"),
        ("Benchmark", "en", "A standard or point of reference against which things may be compared"),
        ("Synergy", "en", "The interaction of cooperation of two or more organizations"),
        ("Optimization", "en", "The action of making the best or most effective use of a resource"),
        ("Itinerary", "en", "A planned route or journey"),
        ("Accommodation", "en", "A room, group of rooms, or building in which someone may live or stay"),
        ("Reservation", "en", "The action of reserving something"),
        ("Backpack", "en", "A bag with shoulder straps that allow it to be carried on one's back"),
        ("Passport", "en", "An official document certifying the holder's identity and citizenship"),
        ("Departure", "en", "The action of leaving, especially to start a journey"),
        ("Luggage", "en", "Suitcases or other bags in which to pack personal belongings for traveling"),
        ("Souvenir", "en", "A thing that is kept as a reminder of a person, place, or event"),
        ("Hypothesis", "en", "A supposition or proposed explanation made on the basis of limited evidence"),
        ("Analysis", "en", "Detailed examination of the elements or structure of something"),
        ("Methodology", "en", "A system of methods used in a particular area of study or activity"),
        ("Citation", "en", "A quotation from or reference to a book, paper, or author"),
        ("Conclusion", "en", "A judgment or decision reached by reasoning"),
        ("Negociación", "es", "English: Negotiation - Discussion to reach agreement"),
        ("Estrategia", "es", "English: Strategy - Plan of action"),
        ("Inversión", "es", "English: Investment"),
        ("Innovación", "es", "English: Innovation"),
        ("Fecha límite", "es", "English: Deadline"),
        ("Itinerario", "es", "English: Itinerary"),
        ("Alojamiento", "es", "English: Accommodation"),
        ("Reservación", "es", "English: Reservation"),
        ("Hipótesis", "es", "English: Hypothesis"),
        ("Análisis", "es", "English: Analysis"),
        ("Desarrollo", "es", "English: Development"),
        ("Mercado", "es", "English: Market"),
        ("Empresa", "es", "English: Company"),
        ("Éxito", "es", "English: Success"),
        ("Viaje", "es", "English: Trip"),
        ("Universidad", "es", "English: University"),
        ("Biblioteca", "es", "English: Library"),
        ("Conocimiento", "es", "English: Knowledge"),
        ("Futuro", "es", "English: Future"),
        ("Proyecto", "es", "English: Project"),
        ("समझौता (Samjhauta)", "hi", "English: Agreement/Compromise"),
        ("रणनीति (Ran-neeti)", "hi", "English: Strategy"),
        ("निवेश (Nivesh)", "hi", "English: Investment"),
        ("नवाचार (Navachar)", "hi", "English: Innovation"),
        ("समय सीमा (Samay Seema)", "hi", "English: Deadline"),
        ("यात्रा कार्यक्रम (Yatra Karyakram)", "hi", "English: Itinerary"),
        ("आवास (Awas)", "hi", "English: Accommodation"),
        ("आरक्षण (Arakshan)", "hi", "English: Reservation"),
        ("परिकल्पना (Parikalpana)", "hi", "English: Hypothesis"),
        ("विश्लेषण (Vishleshan)", "hi", "English: Analysis"),
        ("विकास (Vikas)", "hi", "English: Development"),
        ("बाज़ार (Bazaar)", "hi", "English: Market"),
        ("सफलता (Safalta)", "hi", "English: Success"),
        ("व्यापार (Vyapar)", "hi", "English: Business"),
        ("ज्ञान (Gyaan)", "hi", "English: Knowledge"),
        ("शिक्षा (Shiksha)", "hi", "English: Education"),
        ("अनुसंधान (Anusandhan)", "hi", "English: Research"),
        ("प्रौद्योगिकी (Praudyogiki)", "hi", "English: Technology"),
        ("संचार (Sanchar)", "hi", "English: Communication"),
        ("नेतृत्व (Netritva)", "hi", "English: Leadership")
    ]
    
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS vocabulary_bank (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT UNIQUE, source_word TEXT, meaning TEXT, generated_date TEXT, is_validated INTEGER DEFAULT 0, language TEXT)")
        
        # Generate 5 words
        for _ in range(5):
            word, lang, meaning = "", "", ""
            
            # Priority: Context aware
            if source_pool:
                word_raw = random.choice(source_pool)
                word = word_raw.title()
                # Try to find pre-defined meaning in local_vocab if exists
                match = next((x for x in local_vocab if x[0].lower() == word.lower()), None)
                if match:
                    _, lang, meaning = match
                else:
                    lang = seed_lang if seed_lang else 'en'
                    meaning = f"Related to {seed_word}"
            else:
                # Random fallback
                choice = random.choice(local_vocab)
                word, lang, meaning = choice
                source_context = "General Bank"

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Insert into DB
            try:
                conn.execute("INSERT INTO vocabulary_bank (word, source_word, meaning, generated_date, language) VALUES (?, ?, ?, ?, ?)", 
                            (word, source_context, meaning, ts, lang))
            except:
                try:
                    conn.execute("UPDATE vocabulary_bank SET generated_date=?, source_word=? WHERE word=?", (ts, source_context, word))
                except: pass

            new_words.append({
                "word": word, 
                "language": lang, 
                "source": source_context, 
                "meaning": meaning, 
                "date": ts
            })
            
        conn.commit()
    except Exception as e:
        print(f"Gen error: {e}")
    finally:
        conn.close()
        
    return jsonify(new_words)

@app.route("/api/get_vocabulary_bank_full")
def get_vocab_bank_full():
    conn = sqlite3.connect("vocabulary_bank.db")
    cursor = conn.cursor()
    try:
        # Order by date so recently updated/generated words appear first
        cursor.execute("SELECT word, source_word, generated_date, language FROM vocabulary_bank ORDER BY generated_date DESC LIMIT 50")
        rows = cursor.fetchall()
        result = [{"word": r[0], "source": r[1], "date": r[2], "language": r[3] if len(r)>3 else 'en'} for r in rows]
    except:
        result = []
    conn.close()
    return jsonify(result)

@app.route("/api/get_my_spoken_words")
def get_my_spoken_words():
    """Get the list of unique valid words spoken by the user"""
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    try:
        # Get unique valid words sorted by most recent
        cursor.execute("SELECT DISTINCT word, language, meaning, MAX(timestamp) as last_spoken FROM validation_log WHERE status='valid' GROUP BY word ORDER BY last_spoken DESC LIMIT 50")
        rows = cursor.fetchall()
        result = [{"word": r[0], "language": r[1], "meaning": r[2], "date": r[3]} for r in rows]
    except:
        result = []
    conn.close()
    return jsonify(result)

@app.route("/api/retry_validation")
def retry_validation():
    """Retry validation for all pending entries"""
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    # Find pending items from the log
    try:
        cursor.execute("SELECT id, user_id, word, language FROM validation_log WHERE status='pending'")
        rows = cursor.fetchall()
    except:
        rows = []
    
    conn.close()
    
    processed = 0
    # Process in background to avoid blocking
    def process_retries(items):
        from transcriber import validate_word_online
        for row in items:
            log_id, uid, word, lang = row
            # We call validate_word_online again. 
            # Note: The function inserts a NEW log entry usually. 
            # Ideally we'd modify it to update, but our current implementation creates a new log.
            # To fix this, we'll just let it create a new one (history) and maybe delete the old pending if we want cleaner logs,
            # or just mark old as 'retried'.
            # A simpler way: just run validation. It will create a new entry with potential success.
            # The UI shows latest first, so the user will see the successful one on top.
            try:
                validate_word_online(uid, word, lang)
            except: pass

    if rows:
        threading.Thread(target=process_retries, args=(rows,)).start()
        processed = len(rows)
        
    return jsonify({"message": f"Retrying {processed} pending words in background...", "count": processed})

# Initialize vocabulary bank database
def init_vocab_bank_db():
    conn = sqlite3.connect("vocabulary_bank.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            source_word TEXT,
            meaning TEXT,
            generated_date TEXT,
            is_validated INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_vocab_bank_db()

@app.route("/api/vocabulary_bank")
def get_vocabulary_bank():
    """Generate vocabulary bank using multiple APIs for truly unique words"""
    try:
        import requests
        test_response = requests.get("https://api.datamuse.com/words?ml=test&max=1", timeout=5)
        if test_response.status_code != 200:
            raise Exception("API not accessible")
    except Exception as e:
        return jsonify({"error": f"Offline - Internet required for vocabulary generation ({str(e)})", "words": []})
    
    # Get all existing words from ALL sources
    all_existing_words = set()
    
    # From validated words
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT word FROM validated_words")
    all_existing_words.update([row[0].lower() for row in cursor.fetchall()])
    
    # Get base words from new words and OOV words
    cursor.execute("SELECT DISTINCT word, language FROM validated_words WHERE is_valid = 1 ORDER BY timestamp DESC LIMIT 10")
    validated_data = cursor.fetchall()
    conn.close()
    
    # Get OOV words from chatbot
    oov_words = []
    try:
        chatbot_conn = sqlite3.connect("chatbot_learning.db")
        chatbot_cursor = chatbot_conn.cursor()
        chatbot_cursor.execute("SELECT DISTINCT word, language FROM oov_words ORDER BY timestamp DESC LIMIT 10")
        oov_words = chatbot_cursor.fetchall()
        chatbot_conn.close()
    except:
        pass
    
    # Combine all base words
    all_base_words = validated_data + oov_words
    base_words_by_lang = {'en': [], 'es': [], 'hi': []}
    for word, lang in all_base_words:
        if lang and lang in base_words_by_lang:
            base_words_by_lang[lang].append(word)
    
    # From transcripts
    trans_conn = sqlite3.connect("transcriptions.db")
    trans_cursor = trans_conn.cursor()
    trans_cursor.execute("SELECT DISTINCT text FROM transcripts")
    for row in trans_cursor.fetchall():
        words = [w.strip('.,!?;:"()[]').lower() for w in row[0].split() if len(w) > 2 and w.isalpha()]
        all_existing_words.update(words)
    trans_conn.close()
    
    # From vocabulary bank
    vocab_conn = sqlite3.connect("vocabulary_bank.db")
    vocab_cursor = vocab_conn.cursor()
    vocab_cursor.execute("SELECT DISTINCT word FROM vocabulary_bank")
    all_existing_words.update([row[0].lower() for row in vocab_cursor.fetchall()])
    vocab_conn.close()
    
    # From chatbot data
    try:
        chatbot_conn = sqlite3.connect("chatbot_learning.db")
        chatbot_cursor = chatbot_conn.cursor()
        chatbot_cursor.execute("SELECT DISTINCT word FROM user_vocabulary")
        all_existing_words.update([row[0].lower() for row in chatbot_cursor.fetchall()])
        chatbot_cursor.execute("SELECT DISTINCT word FROM oov_words")
        all_existing_words.update([row[0].lower() for row in chatbot_cursor.fetchall()])
        chatbot_conn.close()
    except:
        pass
    
    if not any(base_words_by_lang.values()):
        return jsonify({"words": [], "message": "No validated words found. Speak more to build vocabulary."})
    
    new_vocabulary = set()
    
    try:
        import requests
        import random
        
        new_vocabulary_by_lang = {'en': set(), 'es': set(), 'hi': set()}
        target_counts = {'en': 5, 'hi': 3, 'es': 2}  # 50%, 30%, 20%
        
        # English words - exactly 5 words (50%)
        en_sources = base_words_by_lang['en'] if base_words_by_lang['en'] else ['water', 'house', 'book']
        for base_word in en_sources[:1]:
            try:
                url = f"https://api.datamuse.com/words?ml={base_word}&max=15"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    count = 0
                    for item in data:
                        if count >= target_counts['en']:
                            break
                        word = item.get('word', '').lower()
                        if len(word) > 3 and word.isalpha() and word not in all_existing_words:
                            new_vocabulary_by_lang['en'].add(word)
                            count += 1
            except:
                continue
        
        # Hindi words - exactly 3 words (30%)
        hi_base_words = ['water', 'house', 'book', 'time', 'work', 'love', 'good', 'new', 'big', 'small']
        count = 0
        for base_word in hi_base_words:
            if count >= target_counts['hi']:
                break
            try:
                url = f"https://api.mymemory.translated.net/get?q={base_word}&langpair=en|hi"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    hi_word = data.get('responseData', {}).get('translatedText', '')
                    if len(hi_word) > 1 and hi_word not in all_existing_words:
                        new_vocabulary_by_lang['hi'].add(hi_word)
                        count += 1
            except:
                continue
        
        # Spanish words - exactly 2 words (20%)
        es_base_words = ['water', 'house', 'book', 'time', 'work', 'love', 'good', 'new', 'big', 'small']
        count = 0
        for base_word in es_base_words:
            if count >= target_counts['es']:
                break
            try:
                url = f"https://api.mymemory.translated.net/get?q={base_word}&langpair=en|es"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    es_word = data.get('responseData', {}).get('translatedText', '').lower()
                    if len(es_word) > 2 and es_word not in all_existing_words:
                        new_vocabulary_by_lang['es'].add(es_word)
                        count += 1
            except:
                continue
        

        

        
        # Combine all languages
        for lang_words in new_vocabulary_by_lang.values():
            new_vocabulary.update(lang_words)
    
    except Exception as e:
        print(f"Vocabulary generation error: {e}")
        return jsonify({"error": f"Generation failed: {str(e)}", "words": []})
    
    # Convert to list and limit to 10 words per generation
    final_vocab = list(new_vocabulary)[:10]
    
    # Store in vocabulary bank with language detection
    if final_vocab:
        vocab_conn = sqlite3.connect("vocabulary_bank.db")
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Add language column if not exists
        try:
            vocab_conn.execute("ALTER TABLE vocabulary_bank ADD COLUMN language TEXT DEFAULT 'en'")
        except:
            pass
        
        for word in final_vocab:
            # Detect language
            word_lang = 'en'
            if any(c in word for c in 'áéíóúüñ'):
                word_lang = 'es'
            elif any(ord(c) > 2304 and ord(c) < 2432 for c in word):
                word_lang = 'hi'
            
            try:
                vocab_conn.execute(
                    "INSERT OR IGNORE INTO vocabulary_bank (word, source_word, generated_date, language) VALUES (?, ?, ?, ?)",
                    (word, f"{word_lang} base words", timestamp, word_lang)
                )
            except:
                pass
        
        vocab_conn.commit()
        vocab_conn.close()
    
    # Group results by language
    vocab_by_lang = {'en': [], 'es': [], 'hi': []}
    for word in final_vocab:
        if any(c in word for c in 'áéíóúüñ'):
            vocab_by_lang['es'].append(word)
        elif any(ord(c) > 2304 and ord(c) < 2432 for c in word):
            vocab_by_lang['hi'].append(word)
        else:
            vocab_by_lang['en'].append(word)
    
    return jsonify({
        "words": final_vocab,
        "words_by_language": vocab_by_lang,
        "base_words_by_lang": base_words_by_lang,
        "total_generated": len(final_vocab), 
        "excluded_count": len(all_existing_words),
        "message": f"Generated {len(final_vocab)}/10 words (50% EN, 30% HI, 20% ES): EN({len(vocab_by_lang['en'])}), HI({len(vocab_by_lang['hi'])}), ES({len(vocab_by_lang['es'])})"
    })

@app.route("/api/clear_all_data", methods=["POST"])
def clear_all_data():
    """Clear all database records and start fresh"""
    try:
        # Clear transcriptions
        conn1 = sqlite3.connect("transcriptions.db")
        conn1.execute("DELETE FROM transcripts")
        conn1.commit()
        conn1.close()
        
        # Clear validated words
        conn2 = sqlite3.connect("word_database.db")
        conn2.execute("DELETE FROM validated_words")
        conn2.commit()
        conn2.close()
        
        # Clear adaptive tutor data and vocabulary bank
        try:
            from adaptive_chatbot import AdaptiveChatbot
            chatbot = AdaptiveChatbot()
            chatbot.clear_all_adaptive_data()
            
            # Clear vocabulary bank
            conn4 = sqlite3.connect("vocabulary_bank.db")
            conn4.execute("DELETE FROM vocabulary_bank")
            conn4.commit()
            conn4.close()
        except:
            pass
        
        # Clear audio files
        import glob
        audio_files = glob.glob("audio_clips/*.wav")
        for file in audio_files:
            try:
                os.remove(file)
            except:
                pass
        
        return jsonify({"status": "success", "message": "All data cleared successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/get_stored_vocab_bank")
def get_stored_vocab_bank():
    """Get stored vocabulary bank words"""
    conn = sqlite3.connect("vocabulary_bank.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word, source_word, generated_date FROM vocabulary_bank ORDER BY generated_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"word": r[0], "source": r[1], "date": r[2]} for r in rows])

@app.route("/api/clear_vocab_bank", methods=["POST"])
def clear_vocab_bank():
    """Clear vocabulary bank"""
    try:
        conn = sqlite3.connect("vocabulary_bank.db")
        conn.execute("DELETE FROM vocabulary_bank")
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Vocabulary bank cleared"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/clear_tutor_all", methods=["POST"])
def clear_tutor_all():
    """Clear all tutor/learning data and start completely fresh"""
    try:
        # Clear chatbot learning data
        try:
            chatbot_conn = sqlite3.connect("chatbot_learning.db")
            chatbot_conn.execute("DELETE FROM user_vocabulary")
            chatbot_conn.execute("DELETE FROM oov_words")
            chatbot_conn.execute("DELETE FROM user_performance")
            chatbot_conn.commit()
            chatbot_conn.close()
        except:
            pass
        
        # Clear vocabulary bank
        vocab_conn = sqlite3.connect("vocabulary_bank.db")
        vocab_conn.execute("DELETE FROM vocabulary_bank")
        vocab_conn.commit()
        vocab_conn.close()
        
        # Clear validated words
        word_conn = sqlite3.connect("word_database.db")
        word_conn.execute("DELETE FROM validated_words")
        word_conn.commit()
        word_conn.close()
        
        return jsonify({"status": "success", "message": "All tutor data cleared - fresh start!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/clear_tutor_new_words", methods=["POST"])
def clear_tutor_new_words():
    """Clear only new words (user vocabulary)"""
    try:
        chatbot_conn = sqlite3.connect("chatbot_learning.db")
        chatbot_conn.execute("DELETE FROM user_vocabulary")
        chatbot_conn.commit()
        chatbot_conn.close()
        
        return jsonify({"status": "success", "message": "New words cleared"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/clear_tutor_oov", methods=["POST"])
def clear_tutor_oov():
    """Clear only OOV (Out of Vocabulary) words"""
    try:
        chatbot_conn = sqlite3.connect("chatbot_learning.db")
        chatbot_conn.execute("DELETE FROM oov_words")
        chatbot_conn.commit()
        chatbot_conn.close()
        
        return jsonify({"status": "success", "message": "OOV words cleared"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/download/vocab_bank")
def download_vocab_bank():
    """Download vocabulary bank as CSV"""
    conn = sqlite3.connect("vocabulary_bank.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word, source_word, generated_date FROM vocabulary_bank ORDER BY generated_date DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Word", "Source Words", "Generated Date"])
    
    for row in rows:
        writer.writerow([row[0], row[1], row[2]])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=vocabulary_bank.csv"}
    )

@app.route("/download/validations")
def download_validations():
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    
    # Check table structure
    cursor.execute("PRAGMA table_info(validated_words)")
    columns = [col[1] for col in cursor.fetchall()]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Word", "Language", "Status", "Meaning", "Timestamp"])
    
    if 'timestamp' in columns and 'is_valid' in columns:
        cursor.execute("SELECT word, language, meaning, is_valid, timestamp FROM validated_words ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        for row in rows:
            status = "Valid" if row[3] else "Invalid"
            writer.writerow([row[0], row[1] or "EN", status, row[2] or "", row[4]])
    else:
        cursor.execute("SELECT word, language, meaning FROM validated_words ORDER BY rowid DESC")
        rows = cursor.fetchall()
        import time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        for row in rows:
            writer.writerow([row[0], row[1] or "EN", "Valid", row[2] or "", current_time])
    
    conn.close()
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=word_validations.csv"}
    )

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/vocabulary")
def vocabulary_page():
    return render_template("vocabulary.html")

@app.route("/dataset")
def dataset_page():
    return render_template("dataset.html")

@app.route("/data")
def data():
    lang = request.args.get("lang", "all")
    return jsonify(get_transcripts(limit=20, lang=lang))

# 🔹 Download TXT
@app.route("/download/txt")
def download_txt():
    transcripts = get_transcripts()
    output = io.StringIO()
    for t in transcripts:
        output.write(f"{t['timestamp']} [{t['language']}] - {t['text']}\n")
    return Response(output.getvalue(),
                    mimetype="text/plain",
                    headers={"Content-Disposition": "attachment;filename=transcripts.txt"})

# 🔹 Download CSV
@app.route("/download/csv")
def download_csv():
    transcripts = get_transcripts()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Language", "Transcript", "AudioFile"])
    for t in transcripts:
        writer.writerow([t['timestamp'], t['language'], t['text'], t['audio_file']])
    return Response(output.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=transcripts.csv"})

# 🔹 Serve audio files
@app.route("/audio_clips/<path:filename>")
def download_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route("/validate_word")
def validate_word():
    word = request.args.get("word")
    language = request.args.get("lang", "en")
    user_id = request.args.get("user", "default_user")
    if not word:
        return jsonify({"error": "Word parameter required"})
    result = word_validator.validate_and_store_word(user_id, word, language)
    return jsonify(result)

@app.route("/user_words")
def get_user_words():
    user_id = request.args.get("user", "default_user")
    language = request.args.get("lang")
    words = word_validator.get_user_words(user_id, language)
    return jsonify(words)

@app.route("/detect_language")
def detect_language():
    text = request.args.get("text", "")
    detected = lang_detector.detect_language(text)
    return jsonify({"text": text, "detected_language": detected})


# -------- Adaptive Chatbot + Tutor Endpoints --------
def _user():
    return request.args.get("user", "default_user")


@app.route("/chatbot/vocabulary")
def chatbot_vocabulary():
    user_id = _user()
    language = request.args.get("lang")
    limit = int(request.args.get("limit", 200))
    vocab = chatbot.get_vocabulary(user_id, language, limit=limit)
    return jsonify({"user": user_id, "items": vocab})


@app.route("/chatbot/new_words")
def chatbot_new_words():
    user_id = _user()
    language = request.args.get("lang")
    days = int(request.args.get("days", 7))
    data = chatbot.get_new_words_by_date(user_id, days=days, language=language)
    return jsonify({"user": user_id, "days": days, "by_date": data})


@app.route("/chatbot/oov")
def chatbot_oov():
    user_id = _user()
    language = request.args.get("lang")
    oov = chatbot.get_oov_words(user_id, language)
    return jsonify({"user": user_id, "items": oov})


@app.route("/chatbot/stats")
def chatbot_stats():
    user_id = _user()
    language = request.args.get("lang")
    stats = chatbot.get_user_stats(user_id, language)
    return jsonify({"user": user_id, "stats": stats})


@app.route("/chatbot/lesson")
def chatbot_lesson():
    user_id = _user()
    language = request.args.get("lang", "en")
    lesson = chatbot.get_personalized_lesson(user_id, language)
    return jsonify({"user": user_id, "language": language, "lesson": lesson})


@app.route("/chatbot/daily_challenge")
def chatbot_daily_challenge():
    user_id = _user()
    language = request.args.get("lang", "en")
    challenge = chatbot.get_daily_challenge(user_id, language)
    return jsonify({"user": user_id, "language": language, "challenge": challenge})


@app.route("/chatbot/record_performance", methods=["POST"])
def chatbot_record_performance():
    payload = request.get_json(force=True, silent=True) or {}
    user_id = payload.get("user", "default_user")
    language = payload.get("lang", "en")
    chatbot.record_performance(
        user_id=user_id,
        language=language,
        word=payload.get("word"),
        lesson_type=payload.get("lesson_type", "practice"),
        response_time=float(payload.get("response_time", 0)),
        is_correct=bool(payload.get("is_correct", False)),
        difficulty_level=payload.get("difficulty_level", "beginner"),
    )
    return jsonify({"status": "recorded"})


@app.route("/chatbot/analytics")
def chatbot_analytics():
    """Aggregate stats for dashboard charts."""
    user_id = request.args.get("user", "default_user")
    stats = chatbot.get_user_stats(user_id)

    # XP per language
    xp_by_lang = {}
    for lang, s in stats.items():
        xp_by_lang[lang] = s.get("total_xp") or s.get("xp") or 0

    # New words count by date (last 7 days)
    new_words_raw = chatbot.get_new_words_by_date(user_id, days=7)
    new_words_by_day = {day: len(words) for day, words in new_words_raw.items()}

    # OOV counts per language
    oov_items = chatbot.get_oov_words(user_id)
    oov_by_lang = {}
    for item in oov_items:
        oov_by_lang[item["language"]] = oov_by_lang.get(item["language"], 0) + item.get("occurrences", 1)

    return jsonify({
        "xp_by_lang": xp_by_lang,
        "new_words_by_day": new_words_by_day,
        "oov_by_lang": oov_by_lang
    })


@app.route("/record/start", methods=["POST"])
def record_start():
    transcriber.stop_event.clear()
    transcriber.start_transcriber()
    return jsonify({"recording": True})


@app.route("/record/stop", methods=["POST"])
def record_stop():
    transcriber.stop_transcriber()
    return jsonify({"recording": False})


@app.route("/record/status")
def record_status():
    running = transcriber.listener_thread is not None and transcriber.listener_thread.is_alive()
    return jsonify({"recording": running})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
