import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "linguavoice.db"

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_db(self):
        # Create directory if it doesn't exist (useful for persistent volumes like /app/data)
        db_dir = os.path.dirname(self.db_name)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                target_language TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Transcripts Table (Linked to User)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TEXT,
                language TEXT,
                text TEXT,
                audio_file TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 3. Vocabulary / Words Table (Consolidates validated_words & user_vocabulary)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                language TEXT,
                meaning TEXT,
                is_valid INTEGER DEFAULT 0,
                mastery_level INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_practiced TIMESTAMP,
                frequency INTEGER DEFAULT 1,
                source_context TEXT,
                correct_attempts INTEGER DEFAULT 0,
                incorrect_attempts INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, word, language)
            )
        """)

    # ... (existing imports will be handled by context if I don't touch them, but since I need 'json', checking the top is better. The tool replaces blocks by line numbers)

    # 4. Learning Sessions / Stats (Keep existing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_date DATE,
                language TEXT,
                words_learned INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 5. User Global Progress (Keep existing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                language TEXT,
                total_xp INTEGER DEFAULT 0,
                current_level TEXT DEFAULT 'Beginner',
                streak_days INTEGER DEFAULT 0,
                last_activity DATE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, language)
            )
        """)

        # 6. OOV Words
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oov_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                language TEXT,
                first_seen DATE,
                last_seen DATE,
                occurrences INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, word, language)
            )
        """)

        # NEW: User Completed Levels (Content Map 1-100)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_completed_levels (
                user_id INTEGER, 
                level_id INTEGER, 
                xp_earned INTEGER, 
                score INTEGER, 
                passed BOOLEAN, 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                PRIMARY KEY (user_id, level_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 7. Performance Analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                language TEXT,
                word TEXT,
                lesson_type TEXT,
                response_time REAL,
                is_correct BOOLEAN,
                timestamp DATETIME,
                difficulty_level TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 8. Lessons
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT,
                level TEXT,
                section INTEGER,
                lesson_type TEXT,
                content TEXT,
                difficulty_score INTEGER DEFAULT 1
            )
        """)
        
        # Populate initial lessons if empty
        cursor.execute("SELECT COUNT(*) FROM lessons")
        if cursor.fetchone()[0] == 0:
            import json
            lessons_data = [
                ('en', 'beginner', 1, 'vocabulary', json.dumps({
                    'title': 'Basic Greetings',
                    'words': ['hello', 'goodbye', 'please', 'thank you'],
                    'exercises': [
                        {'type': 'match', 'pairs': [['hello', 'hola'], ['goodbye', 'adiós']]},
                        {'type': 'listen_repeat', 'audio_prompts': ['hello', 'goodbye']},
                        {'type': 'translate', 'sentences': ['Hello, how are you?']}
                    ]
                }), 1),
                ('en', 'intermediate', 2, 'grammar', json.dumps({
                    'title': 'Present Perfect Tense',
                    'concepts': ['have/has + past participle'],
                    'examples': ['I have eaten', 'She has worked'],
                    'exercises': [
                        {'type': 'fill_blank', 'sentence': 'I ___ (eat) breakfast', 'answer': 'have eaten'},
                        {'type': 'correct_mistake', 'wrong': 'I have ate', 'correct': 'I have eaten'}
                    ]
                }), 3),
                ('es', 'beginner', 1, 'vocabulary', json.dumps({
                    'title': 'Saludos Básicos',
                    'words': ['hola', 'adiós', 'por favor', 'gracias'],
                    'exercises': [
                        {'type': 'match', 'pairs': [['hola', 'hello'], ['adiós', 'goodbye']]},
                        {'type': 'pronunciation', 'words': ['hola', 'gracias']}
                    ]
                }), 1),
            ]
            cursor.executemany(
                "INSERT INTO lessons (language, level, section, lesson_type, content, difficulty_score) VALUES (?, ?, ?, ?, ?, ?)",
                lessons_data
            )

        conn.commit()
        conn.close()

    # --- User Management Methods ---
    def register_user(self, email, password, name, target_language="es"):
        conn = self.get_connection()
        try:
            password_hash = generate_password_hash(password)
            conn.execute("INSERT INTO users (email, password_hash, name, target_language) VALUES (?, ?, ?, ?)", 
                         (email, password_hash, name, target_language))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def login_user(self, email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Add target_language to selection
        try:
            cursor.execute("SELECT id, password_hash, name, target_language FROM users WHERE email=?", (email,))
        except:
            # Fallback if column doesn't exist yet (migration)
            cursor.execute("SELECT id, password_hash, name FROM users WHERE email=?", (email,))
            
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            lang = user[3] if len(user) > 3 else None
            return {"id": user[0], "name": user[2], "email": email, "target_language": lang}
        return None

    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, name, email, target_language FROM users WHERE id=?", (user_id,))
        except:
             cursor.execute("SELECT id, name, email FROM users WHERE id=?", (user_id,))
             
        user = cursor.fetchone()
        conn.close()
        if user:
            lang = user[3] if len(user) > 3 else None
            return {"id": user[0], "name": user[1], "email": user[2], "target_language": lang}
        return None

db = DatabaseManager()
