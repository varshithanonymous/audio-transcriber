from flask import Flask, render_template, jsonify, Response, send_from_directory, request
import sqlite3
import csv
import io
import os
import transcriber
from adaptive_chatbot import AdaptiveChatbot

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
    return render_template("main_menu.html")

@app.route("/transcription")
def transcription_page():
    return render_template("transcription.html")

@app.route("/tutor")
def tutor_page():
    return render_template("tutor.html")

@app.route("/validation_page")
def validation_page():
    return render_template("validation.html")

@app.route("/validation")
def validation_redirect():
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

@app.route("/api/get_all_words")
def get_all_validated_words():
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    
    # Check if table exists and get column info
    cursor.execute("PRAGMA table_info(validated_words)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'timestamp' in columns and 'is_valid' in columns:
        cursor.execute("SELECT word, language, meaning, is_valid, timestamp FROM validated_words ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        result = [{"word": r[0], "language": r[1] or "EN", "meaning": r[2], "is_valid": bool(r[3]), "timestamp": r[4]} for r in rows]
    else:
        # Fallback for older table structure
        cursor.execute("SELECT word, language, meaning FROM validated_words ORDER BY rowid DESC")
        rows = cursor.fetchall()
        import time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        result = [{"word": r[0], "language": r[1] or "EN", "meaning": r[2], "is_valid": True, "timestamp": current_time} for r in rows]
    
    conn.close()
    return jsonify(result)

@app.route("/api/get_pending_words")
def get_pending_words():
    """Get words that are pending validation (stored offline, need online validation)"""
    conn = sqlite3.connect("word_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM validated_words WHERE is_valid = -1 ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return jsonify({"words": [r[0] for r in rows]})

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
    
    # Get base words for generation
    cursor.execute("SELECT DISTINCT word FROM validated_words WHERE is_valid = 1 ORDER BY timestamp DESC LIMIT 10")
    base_words = [row[0] for row in cursor.fetchall()]
    conn.close()
    
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
    
    if not base_words:
        return jsonify({"words": [], "message": "No validated words found. Speak more to build vocabulary."})
    
    new_vocabulary = set()
    
    try:
        import requests
        import random
        
        # Method 1: Use Datamuse API for related words
        for base_word in base_words[:5]:
            try:
                # Get words that mean similar things
                url = f"https://api.datamuse.com/words?ml={base_word}&max=20"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        word = item.get('word', '').lower()
                        if len(word) > 3 and word.isalpha() and word not in all_existing_words:
                            new_vocabulary.add(word)
                
                # Get words that rhyme
                url = f"https://api.datamuse.com/words?rel_rhy={base_word}&max=15"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        word = item.get('word', '').lower()
                        if len(word) > 3 and word.isalpha() and word not in all_existing_words:
                            new_vocabulary.add(word)
                
                # Get words that sound similar
                url = f"https://api.datamuse.com/words?sl={base_word}&max=10"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        word = item.get('word', '').lower()
                        if len(word) > 3 and word.isalpha() and word not in all_existing_words:
                            new_vocabulary.add(word)
            except:
                continue
        
        # Method 2: Use dictionary API for synonyms and related words
        for base_word in base_words[:8]:
            try:
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{base_word}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        meanings = data[0].get('meanings', [])
                        for meaning in meanings:
                            # Get synonyms
                            synonyms = meaning.get('synonyms', [])
                            for syn in synonyms[:15]:
                                if len(syn) > 3 and syn.isalpha() and syn.lower() not in all_existing_words:
                                    new_vocabulary.add(syn.lower())
                            
                            # Get antonyms
                            antonyms = meaning.get('antonyms', [])
                            for ant in antonyms[:10]:
                                if len(ant) > 3 and ant.isalpha() and ant.lower() not in all_existing_words:
                                    new_vocabulary.add(ant.lower())
            except:
                continue
        
        # Method 3: Generate words by topic using Datamuse
        topics = ['education', 'technology', 'nature', 'science', 'art', 'music', 'sports', 'food']
        for topic in random.sample(topics, 3):
            try:
                url = f"https://api.datamuse.com/words?topics={topic}&max=25"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        word = item.get('word', '').lower()
                        if len(word) > 3 and word.isalpha() and word not in all_existing_words:
                            new_vocabulary.add(word)
            except:
                continue
        
        # Method 4: Get words that frequently appear with base words
        for base_word in base_words[:3]:
            try:
                url = f"https://api.datamuse.com/words?lc={base_word}&max=15"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        word = item.get('word', '').lower()
                        if len(word) > 3 and word.isalpha() and word not in all_existing_words:
                            new_vocabulary.add(word)
            except:
                continue
    
    except Exception as e:
        print(f"Vocabulary generation error: {e}")
        return jsonify({"error": f"Generation failed: {str(e)}", "words": []})
    
    # Convert to list and limit to 100 unique words
    final_vocab = list(new_vocabulary)[:100]
    
    # Store in vocabulary bank
    if final_vocab:
        vocab_conn = sqlite3.connect("vocabulary_bank.db")
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        for word in final_vocab:
            try:
                vocab_conn.execute(
                    "INSERT OR IGNORE INTO vocabulary_bank (word, source_word, generated_date) VALUES (?, ?, ?)",
                    (word, ", ".join(base_words[:3]), timestamp)
                )
            except:
                pass
        
        vocab_conn.commit()
        vocab_conn.close()
    
    return jsonify({
        "words": final_vocab, 
        "base_words": base_words, 
        "total_generated": len(final_vocab), 
        "excluded_count": len(all_existing_words),
        "message": f"Generated {len(final_vocab)} unique words from {len(base_words)} base words"
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
