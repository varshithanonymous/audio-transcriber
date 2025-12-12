import sqlite3
import requests
import json
import time
from threading import Lock

class WordValidator:
    def __init__(self, db_file="word_database.db"):
        self.db_file = db_file
        self.lock = Lock()
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validated_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                word TEXT,
                language TEXT,
                meaning TEXT,
                is_valid INTEGER,
                timestamp TEXT,
                UNIQUE(user_id, word, language)
            )
        """)
        conn.commit()
        conn.close()
    
    def is_online(self):
        try:
            requests.get("https://httpbin.org/status/200", timeout=3)
            return True
        except:
            return False
    
    def get_word_meaning(self, word, language):
        if not self.is_online():
            return None
        
        try:
            if language == 'en':
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        meanings = data[0].get('meanings', [])
                        if meanings:
                            definition = meanings[0].get('definitions', [{}])[0].get('definition', '')
                            return definition
            return None
        except:
            return None
    
    def validate_and_store_word(self, user_id, word, language):
        with self.lock:
            # Check if already validated
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT meaning, is_valid FROM validated_words WHERE user_id=? AND word=? AND language=?",
                (user_id, word.lower(), language)
            )
            result = cursor.fetchone()
            
            if result:
                conn.close()
                return {'cached': True, 'meaning': result[0], 'is_valid': bool(result[1])}
            
            # Validate online if available
            meaning = self.get_word_meaning(word, language)
            is_valid = meaning is not None
            
            # Store result
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT OR REPLACE INTO validated_words (user_id, word, language, meaning, is_valid, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, word.lower(), language, meaning or '', int(is_valid), timestamp)
            )
            conn.commit()
            conn.close()
            
            return {'cached': False, 'meaning': meaning, 'is_valid': is_valid}
    
    def get_user_words(self, user_id, language=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if language:
            cursor.execute(
                "SELECT word, language, meaning, is_valid, timestamp FROM validated_words WHERE user_id=? AND language=? ORDER BY timestamp DESC",
                (user_id, language)
            )
        else:
            cursor.execute(
                "SELECT word, language, meaning, is_valid, timestamp FROM validated_words WHERE user_id=? ORDER BY timestamp DESC",
                (user_id,)
            )
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'word': r[0], 'language': r[1], 'meaning': r[2], 'is_valid': bool(r[3]), 'timestamp': r[4]} for r in results]