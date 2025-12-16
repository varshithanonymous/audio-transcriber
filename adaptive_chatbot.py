import sqlite3
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

class AdaptiveChatbot:
    def __init__(self, db_file="chatbot_learning.db"):
        self.db_file = db_file
        self.init_database()
        
        # Offline vocabulary for 3 languages
        self.offline_vocab = {
            'en': self.load_offline_vocab('en'),
            'es': self.load_offline_vocab('es'), 
            'hi': self.load_offline_vocab('hi')
        }
        
        # Learning patterns
        self.difficulty_levels = ['beginner', 'intermediate', 'advanced', 'proficient']
        self.lesson_types = ['vocabulary', 'grammar', 'listening', 'speaking', 'reading']
    
    def init_database(self):
        conn = sqlite3.connect(self.db_file)
        
        # User vocabulary tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                word TEXT,
                language TEXT,
                first_encountered DATE,
                frequency INTEGER DEFAULT 1,
                mastery_level INTEGER DEFAULT 0,
                last_practiced DATE,
                correct_attempts INTEGER DEFAULT 0,
                incorrect_attempts INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                UNIQUE(user_id, word, language)
            )
        """)

        # Track out-of-vocabulary (OOV) words spotted while offline
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oov_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                word TEXT,
                language TEXT,
                first_seen DATE,
                last_seen DATE,
                occurrences INTEGER DEFAULT 1,
                UNIQUE(user_id, word, language)
            )
        """)
        
        # Daily learning sessions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_date DATE,
                language TEXT,
                words_learned INTEGER DEFAULT 0,
                accuracy_rate REAL DEFAULT 0,
                session_duration INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0
            )
        """)
        
        # User progress tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                language TEXT,
                current_level TEXT DEFAULT 'beginner',
                total_xp INTEGER DEFAULT 0,
                streak_days INTEGER DEFAULT 0,
                last_activity DATE,
                sections_completed INTEGER DEFAULT 0,
                UNIQUE(user_id, language)
            )
        """)
        
        # Lesson content and structure
        conn.execute("""
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
        
        # User performance analytics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                language TEXT,
                word TEXT,
                lesson_type TEXT,
                response_time REAL,
                is_correct BOOLEAN,
                timestamp DATETIME,
                difficulty_level TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        self.populate_initial_lessons()
    
    def load_offline_vocab(self, language):
        """Load offline vocabulary for each language (simulated)"""
        vocab_sets = {
            'en': {
                'basic': ['hello', 'goodbye', 'please', 'thank', 'yes', 'no', 'water', 'food', 'house', 'family'],
                'intermediate': ['beautiful', 'important', 'different', 'possible', 'available', 'necessary'],
                'advanced': ['sophisticated', 'comprehensive', 'extraordinary', 'magnificent', 'tremendous']
            },
            'es': {
                'basic': ['hola', 'adiós', 'por favor', 'gracias', 'sí', 'no', 'agua', 'comida', 'casa', 'familia'],
                'intermediate': ['hermoso', 'importante', 'diferente', 'posible', 'disponible', 'necesario'],
                'advanced': ['sofisticado', 'comprensivo', 'extraordinario', 'magnífico', 'tremendo']
            },
            'hi': {
                'basic': ['namaste', 'alvida', 'kripaya', 'dhanyawad', 'haan', 'nahin', 'paani', 'khana', 'ghar', 'parivar'],
                'intermediate': ['sundar', 'mahattvapurna', 'alag', 'sambhav', 'uplabdh', 'aavashyak'],
                'advanced': ['pariskhrit', 'vyapak', 'asadharan', 'shानदार', 'bhayanak']
            }
        }
        return vocab_sets.get(language, {})
    
    def populate_initial_lessons(self):
        """Create structured lesson content"""
        conn = sqlite3.connect(self.db_file)
        
        lessons_data = [
            # Beginner English
            ('en', 'beginner', 1, 'vocabulary', json.dumps({
                'title': 'Basic Greetings',
                'words': ['hello', 'goodbye', 'please', 'thank you'],
                'exercises': [
                    {'type': 'match', 'pairs': [['hello', 'hola'], ['goodbye', 'adiós']]},
                    {'type': 'listen_repeat', 'audio_prompts': ['hello', 'goodbye']},
                    {'type': 'translate', 'sentences': ['Hello, how are you?']}
                ]
            }), 1),
            
            # Intermediate English
            ('en', 'intermediate', 2, 'grammar', json.dumps({
                'title': 'Present Perfect Tense',
                'concepts': ['have/has + past participle'],
                'examples': ['I have eaten', 'She has worked'],
                'exercises': [
                    {'type': 'fill_blank', 'sentence': 'I ___ (eat) breakfast', 'answer': 'have eaten'},
                    {'type': 'correct_mistake', 'wrong': 'I have ate', 'correct': 'I have eaten'}
                ]
            }), 3),
            
            # Spanish lessons
            ('es', 'beginner', 1, 'vocabulary', json.dumps({
                'title': 'Saludos Básicos',
                'words': ['hola', 'adiós', 'por favor', 'gracias'],
                'exercises': [
                    {'type': 'match', 'pairs': [['hola', 'hello'], ['adiós', 'goodbye']]},
                    {'type': 'pronunciation', 'words': ['hola', 'gracias']}
                ]
            }), 1),
        ]
        
        for lesson in lessons_data:
            conn.execute(
                "INSERT OR IGNORE INTO lessons (language, level, section, lesson_type, content, difficulty_score) VALUES (?, ?, ?, ?, ?, ?)",
                lesson
            )
        
        conn.commit()
        conn.close()
    
    def process_spoken_words(self, user_id, text, language, session_id=None):
        """Process newly spoken words and update vocabulary"""
        words = self.extract_words(text)
        new_words = []
        oov_words = []
        
        conn = sqlite3.connect(self.db_file)
        today = datetime.now().date()
        
        for word in words:
            word_lower = word.lower()
            
            # Check if word exists in offline vocabulary
            is_known = self.is_word_in_offline_vocab(word_lower, language)
            
            # Check if user has encountered this word before
            cursor = conn.cursor()
            cursor.execute(
                "SELECT frequency, mastery_level FROM user_vocabulary WHERE user_id=? AND word=? AND language=?",
                (user_id, word_lower, language)
            )
            result = cursor.fetchone()
            
            if result:
                # Update frequency for existing word
                frequency, mastery = result
                conn.execute(
                    "UPDATE user_vocabulary SET frequency=?, last_practiced=? WHERE user_id=? AND word=? AND language=?",
                    (frequency + 1, today, user_id, word_lower, language)
                )
            else:
                # New word for this user
                conn.execute(
                    "INSERT INTO user_vocabulary (user_id, word, language, first_encountered, last_practiced) VALUES (?, ?, ?, ?, ?)",
                    (user_id, word_lower, language, today, today)
                )
                new_words.append(word_lower)
                
                if not is_known:
                    oov_words.append(word_lower)

                    # Persist OOV tracking for offline improvement
                    conn.execute("""
                        INSERT INTO oov_words (user_id, word, language, first_seen, last_seen, occurrences)
                        VALUES (?, ?, ?, ?, ?, 1)
                        ON CONFLICT(user_id, word, language)
                        DO UPDATE SET last_seen=excluded.last_seen, occurrences=occurrences+1
                    """, (user_id, word_lower, language, today, today))
        
        conn.commit()
        conn.close()
        
        # Update daily session stats
        self.update_session_stats(user_id, language, len(new_words))
        
        return {
            'total_words': len(words),
            'new_words': new_words,
            'oov_words': oov_words,
            'new_word_count': len(new_words)
        }

    def get_new_words_by_date(self, user_id, days=7, language=None):
        """Return newly encountered words grouped by day."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        params = [user_id]
        lang_filter = ""
        if language:
            lang_filter = "AND language=?"
            params.append(language)

        cursor.execute(f"""
            SELECT first_encountered, word, language
            FROM user_vocabulary
            WHERE user_id=? {lang_filter}
              AND first_encountered >= date('now', ? || ' days')
            ORDER BY first_encountered DESC
        """, params + [ str(-abs(days)) ])

        rows = cursor.fetchall()
        conn.close()

        grouped = {}
        for date_str, word, lang in rows:
            grouped.setdefault(date_str, []).append({'word': word, 'language': lang})
        return grouped

    def get_oov_words(self, user_id, language=None):
        """Return stored OOV words to surface offline gaps."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        params = [user_id]
        lang_clause = ""
        if language:
            lang_clause = "AND language=?"
            params.append(language)

        cursor.execute(f"""
            SELECT word, language, first_seen, last_seen, occurrences
            FROM oov_words
            WHERE user_id=? {lang_clause}
            ORDER BY last_seen DESC
        """, params)

        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'word': r[0],
                'language': r[1],
                'first_seen': r[2],
                'last_seen': r[3],
                'occurrences': r[4]
            } for r in rows
        ]

    def get_vocabulary(self, user_id, language=None, limit=200):
        """Return user's vocabulary with mastery metadata."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        params = [user_id]
        lang_clause = ""
        if language:
            lang_clause = "AND language=?"
            params.append(language)

        cursor.execute(f"""
            SELECT word, language, first_encountered, frequency, mastery_level,
                   correct_attempts, incorrect_attempts, avg_response_time
            FROM user_vocabulary
            WHERE user_id=? {lang_clause}
            ORDER BY last_practiced DESC
            LIMIT ?
        """, params + [limit])

        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'word': r[0],
                'language': r[1],
                'first_encountered': r[2],
                'frequency': r[3],
                'mastery_level': r[4],
                'correct_attempts': r[5],
                'incorrect_attempts': r[6],
                'avg_response_time': r[7]
            } for r in rows
        ]
    
    def is_word_in_offline_vocab(self, word, language):
        """Check if word exists in offline vocabulary"""
        if language not in self.offline_vocab:
            return False
        
        for level_words in self.offline_vocab[language].values():
            if word in level_words:
                return True
        return False
    
    def extract_words(self, text):
        """Extract meaningful words from text"""
        # Remove punctuation and split
        words = re.findall(r'\b[a-zA-Z\u0900-\u097F\u00C0-\u017F]+\b', text.lower())
        # Filter out very short words and common stop words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'i', 'you', 'he', 'she', 'it'}
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def get_personalized_lesson(self, user_id, language):
        """Generate personalized lesson based on user's progress and weaknesses"""
        conn = sqlite3.connect(self.db_file)
        
        # Get user's current level and progress
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_level, total_xp, sections_completed FROM user_progress WHERE user_id=? AND language=?",
            (user_id, language)
        )
        progress = cursor.fetchone()
        
        if not progress:
            # New user - start with beginner
            level = 'beginner'
            section = 1
        else:
            level, xp, sections = progress
            section = sections + 1
        
        # Get user's weak areas (words with low mastery or high error rate)
        cursor.execute("""
            SELECT word, mastery_level, correct_attempts, incorrect_attempts 
            FROM user_vocabulary 
            WHERE user_id=? AND language=? AND mastery_level < 3
            ORDER BY (correct_attempts * 1.0 / NULLIF(correct_attempts + incorrect_attempts, 0)) ASC
            LIMIT 10
        """, (user_id, language))
        
        weak_words = cursor.fetchall()
        
        # Get appropriate lesson
        cursor.execute(
            "SELECT content FROM lessons WHERE language=? AND level=? ORDER BY section LIMIT 1",
            (language, level)
        )
        lesson_data = cursor.fetchone()
        
        conn.close()
        
        if lesson_data:
            lesson_content = json.loads(lesson_data[0])
            
            # Customize lesson based on weak areas
            if weak_words:
                lesson_content['focus_words'] = [word[0] for word in weak_words[:5]]
                lesson_content['adaptive_note'] = "This lesson focuses on words you're still learning"
            
            return lesson_content
        
        return self.generate_adaptive_lesson(user_id, language, level, weak_words)
    
    def generate_adaptive_lesson(self, user_id, language, level, weak_words):
        """Generate adaptive lesson content"""
        lesson = {
            'title': f'Adaptive {level.title()} Lesson',
            'type': 'adaptive',
            'level': level,
            'exercises': []
        }
        
        if weak_words:
            # Focus on weak words
            lesson['exercises'].extend([
                {
                    'type': 'vocabulary_review',
                    'words': [word[0] for word in weak_words[:5]],
                    'instruction': 'Let\'s practice these words you\'re still learning'
                },
                {
                    'type': 'spaced_repetition',
                    'words': [word[0] for word in weak_words],
                    'instruction': 'Repeat after me to improve pronunciation'
                }
            ])
        
        # Add progressive exercises based on level
        if level == 'beginner':
            lesson['exercises'].extend([
                {
                    'type': 'basic_vocabulary',
                    'words': self.offline_vocab.get(language, {}).get('basic', [])[:10],
                    'instruction': 'Learn these essential words'
                },
                {
                    'type': 'listen_repeat',
                    'instruction': 'Listen and repeat each word'
                }
            ])
        elif level == 'intermediate':
            lesson['exercises'].extend([
                {
                    'type': 'sentence_building',
                    'instruction': 'Build sentences using learned vocabulary'
                },
                {
                    'type': 'grammar_practice',
                    'instruction': 'Practice grammar patterns'
                }
            ])
        
        return lesson
    
    def record_performance(self, user_id, language, word, lesson_type, response_time, is_correct, difficulty_level):
        """Record user performance for analytics"""
        conn = sqlite3.connect(self.db_file)
        
        # Record performance
        conn.execute("""
            INSERT INTO performance_analytics 
            (user_id, language, word, lesson_type, response_time, is_correct, timestamp, difficulty_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, language, word, lesson_type, response_time, is_correct, datetime.now(), difficulty_level))
        
        # Update word mastery
        if word:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT correct_attempts, incorrect_attempts, mastery_level FROM user_vocabulary WHERE user_id=? AND word=? AND language=?",
                (user_id, word, language)
            )
            result = cursor.fetchone()
            
            if result:
                correct, incorrect, mastery = result
                if is_correct:
                    correct += 1
                    # Increase mastery if performance is good
                    if correct > 0 and correct / (correct + incorrect) > 0.8:
                        mastery = min(5, mastery + 1)
                else:
                    incorrect += 1
                    # Decrease mastery if struggling
                    if incorrect > correct:
                        mastery = max(0, mastery - 1)
                
                conn.execute(
                    "UPDATE user_vocabulary SET correct_attempts=?, incorrect_attempts=?, mastery_level=? WHERE user_id=? AND word=? AND language=?",
                    (correct, incorrect, mastery, user_id, word, language)
                )
        
        conn.commit()
        conn.close()
        
        # Award XP and update progress
        xp_earned = 10 if is_correct else 2
        self.update_user_progress(user_id, language, xp_earned)
    
    def update_user_progress(self, user_id, language, xp_earned):
        """Update user's overall progress and level"""
        conn = sqlite3.connect(self.db_file)
        today = datetime.now().date()
        
        cursor = conn.cursor()
        cursor.execute(
            "SELECT total_xp, current_level, streak_days, last_activity FROM user_progress WHERE user_id=? AND language=?",
            (user_id, language)
        )
        result = cursor.fetchone()
        
        if result:
            total_xp, current_level, streak_days, last_activity = result
            new_xp = total_xp + xp_earned
            
            # Update streak
            if last_activity:
                last_date = datetime.strptime(last_activity, '%Y-%m-%d').date()
                if today - last_date == timedelta(days=1):
                    streak_days += 1
                elif today - last_date > timedelta(days=1):
                    streak_days = 1
            else:
                streak_days = 1
            
            # Check for level up
            new_level = self.calculate_level(new_xp)
            
            conn.execute("""
                UPDATE user_progress 
                SET total_xp=?, current_level=?, streak_days=?, last_activity=?
                WHERE user_id=? AND language=?
            """, (new_xp, new_level, streak_days, today, user_id, language))
        else:
            # New user
            conn.execute("""
                INSERT INTO user_progress (user_id, language, total_xp, current_level, streak_days, last_activity)
                VALUES (?, ?, ?, 'beginner', 1, ?)
            """, (user_id, language, xp_earned, today))
        
        conn.commit()
        conn.close()
    
    def calculate_level(self, xp):
        """Calculate user level based on XP"""
        if xp < 100:
            return 'beginner'
        elif xp < 500:
            return 'intermediate'
        elif xp < 1500:
            return 'advanced'
        else:
            return 'proficient'
    
    def get_user_stats(self, user_id, language=None):
        """Get comprehensive user statistics"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        stats = {}
        
        if language:
            # Language-specific stats
            cursor.execute(
                "SELECT total_xp, current_level, streak_days, sections_completed FROM user_progress WHERE user_id=? AND language=?",
                (user_id, language)
            )
            progress = cursor.fetchone()
            
            cursor.execute(
                "SELECT COUNT(*) FROM user_vocabulary WHERE user_id=? AND language=?",
                (user_id, language)
            )
            vocab_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT AVG(CASE WHEN correct_attempts + incorrect_attempts > 0 
                           THEN correct_attempts * 1.0 / (correct_attempts + incorrect_attempts) 
                           ELSE 0 END)
                FROM user_vocabulary WHERE user_id=? AND language=?
            """, (user_id, language))
            accuracy = cursor.fetchone()[0] or 0
            
            stats[language] = {
                'progress': progress,
                'vocabulary_size': vocab_count,
                'accuracy_rate': round(accuracy * 100, 1),
                'level': progress[1] if progress else 'beginner'
            }
        else:
            # All languages
            cursor.execute(
                "SELECT language, total_xp, current_level, streak_days FROM user_progress WHERE user_id=?",
                (user_id,)
            )
            all_progress = cursor.fetchall()
            
            for lang_data in all_progress:
                lang, xp, level, streak = lang_data
                stats[lang] = {
                    'xp': xp,
                    'level': level,
                    'streak': streak
                }
        
        conn.close()
        return stats
    
    def update_session_stats(self, user_id, language, new_words_count):
        """Update daily session statistics"""
        conn = sqlite3.connect(self.db_file)
        today = datetime.now().date()
        
        cursor = conn.cursor()
        cursor.execute(
            "SELECT words_learned FROM learning_sessions WHERE user_id=? AND language=? AND session_date=?",
            (user_id, language, today)
        )
        result = cursor.fetchone()
        
        if result:
            # Update existing session
            conn.execute(
                "UPDATE learning_sessions SET words_learned=words_learned+? WHERE user_id=? AND language=? AND session_date=?",
                (new_words_count, user_id, language, today)
            )
        else:
            # Create new session
            conn.execute(
                "INSERT INTO learning_sessions (user_id, language, session_date, words_learned) VALUES (?, ?, ?, ?)",
                (user_id, language, today, new_words_count)
            )
        
        conn.commit()
        conn.close()
    
    def get_daily_challenge(self, user_id, language):
        """Generate daily challenge based on user's progress"""
        stats = self.get_user_stats(user_id, language)
        
        if not stats.get(language):
            # New user challenge
            return {
                'type': 'vocabulary_introduction',
                'title': 'Welcome! Learn your first 5 words',
                'target': 5,
                'words': self.offline_vocab.get(language, {}).get('basic', [])[:5],
                'xp_reward': 50
            }
        
        user_level = stats[language]['level']
        vocab_size = stats[language]['vocabulary_size']
        
        challenges = {
            'beginner': {
                'type': 'daily_vocabulary',
                'title': 'Learn 3 new words today',
                'target': 3,
                'xp_reward': 30
            },
            'intermediate': {
                'type': 'sentence_practice',
                'title': 'Build 5 sentences using learned words',
                'target': 5,
                'xp_reward': 50
            },
            'advanced': {
                'type': 'conversation_practice',
                'title': 'Practice a 2-minute conversation',
                'target': 120,  # seconds
                'xp_reward': 100
            }
        }
        
        return challenges.get(user_level, challenges['beginner'])
    
    def clear_all_adaptive_data(self):
        """Clear all adaptive tutor data for fresh start"""
        conn = sqlite3.connect(self.db_file)
        
        # Clear all adaptive learning tables
        tables_to_clear = [
            'user_vocabulary',
            'oov_words', 
            'learning_sessions',
            'user_progress',
            'performance_analytics'
        ]
        
        for table in tables_to_clear:
            try:
                conn.execute(f"DELETE FROM {table}")
            except:
                pass
        
        conn.commit()
        conn.close()
        return True