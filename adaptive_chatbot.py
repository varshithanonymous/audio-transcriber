import sqlite3
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from database_manager import db

class AdaptiveChatbot:
    def __init__(self):
        # Offline vocabulary for 3 languages
        self.offline_vocab = {
            'en': self.load_offline_vocab('en'),
            'es': self.load_offline_vocab('es'), 
            'hi': self.load_offline_vocab('hi')
        }
        
        # Learning patterns
        self.difficulty_levels = ['beginner', 'intermediate', 'advanced', 'proficient']
        self.lesson_types = ['vocabulary', 'grammar', 'listening', 'speaking', 'reading']
        
        # Ensure lessons table structure exists (if not created by manager)
        self.populate_initial_lessons()
    
    def get_connection(self):
        return db.get_connection()

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
        """
        Historical method: Table creation is now handled by DatabaseManager.
        This method is kept empty to avoid breaking legacy calls if any.
        """
        pass

    
    def process_spoken_words(self, user_id, text, language, session_id=None):
        """Process newly spoken words and update vocabulary"""
        words = self.extract_words(text)
        new_words = []
        oov_words = []
        
        conn = self.get_connection()
        today = datetime.now().date()
        
        for word in words:
            word_lower = word.lower()
            is_known = self.is_word_in_offline_vocab(word_lower, language)
            
            cursor = conn.cursor()
            cursor.execute(
                "SELECT frequency, mastery_level FROM vocabulary WHERE user_id=? AND word=? AND language=?",
                (user_id, word_lower, language)
            )
            result = cursor.fetchone()
            
            if result:
                frequency, mastery = result
                conn.execute(
                    "UPDATE vocabulary SET frequency=?, last_practiced=? WHERE user_id=? AND word=? AND language=?",
                    (frequency + 1, today, user_id, word_lower, language)
                )
            else:
                conn.execute(
                    "INSERT INTO vocabulary (user_id, word, language, first_seen, last_practiced) VALUES (?, ?, ?, ?, ?)",
                    (user_id, word_lower, language, today, today)
                )
                new_words.append(word_lower)
                
                if not is_known:
                    oov_words.append(word_lower)
                    conn.execute("""
                        INSERT INTO oov_words (user_id, word, language, first_seen, last_seen, occurrences)
                        VALUES (?, ?, ?, ?, ?, 1)
                        ON CONFLICT(user_id, word, language)
                        DO UPDATE SET last_seen=excluded.last_seen, occurrences=occurrences+1
                    """, (user_id, word_lower, language, today, today))
        
        conn.commit()
        conn.close()
        
        self.update_session_stats(user_id, language, len(new_words))
        
        return {
            'total_words': len(words),
            'new_words': new_words,
            'oov_words': oov_words,
            'new_word_count': len(new_words)
        }

    def get_new_words_by_date(self, user_id, days=7, language=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        params = [user_id]
        lang_filter = ""
        if language:
            lang_filter = "AND language=?"
            params.append(language)

        cursor.execute(f"""
            SELECT first_seen, word, language
            FROM vocabulary
            WHERE user_id=? {lang_filter}
              AND first_seen >= date('now', ? || ' days')
            ORDER BY first_seen DESC
        """, params + [ str(-abs(days)) ])

        rows = cursor.fetchall()
        conn.close()

        grouped = {}
        for date_str, word, lang in rows:
            grouped.setdefault(date_str, []).append({'word': word, 'language': lang})
        return grouped

    def get_oov_words(self, user_id, language=None):
        conn = self.get_connection()
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
            {'word': r[0], 'language': r[1], 'first_seen': r[2], 'last_seen': r[3], 'occurrences': r[4]} for r in rows
        ]

    def get_vocabulary(self, user_id, language=None, limit=200):
        conn = self.get_connection()
        cursor = conn.cursor()
        params = [user_id]
        lang_clause = ""
        if language:
            lang_clause = "AND language=?"
            params.append(language)

        cursor.execute(f"""
            SELECT word, language, first_seen, frequency, mastery_level,
                   correct_attempts, incorrect_attempts
            FROM vocabulary
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
                'first_seen': r[2],
                'frequency': r[3],
                'mastery_level': r[4],
                'correct_attempts': r[5],
                'incorrect_attempts': r[6]
            } for r in rows
        ]
    
    def is_word_in_offline_vocab(self, word, language):
        if language not in self.offline_vocab: return False
        for level_words in self.offline_vocab[language].values():
            if word in level_words: return True
        return False
    
    def extract_words(self, text):
        words = re.findall(r'\b[a-zA-Z\u0900-\u097F\u00C0-\u017F]+\b', text.lower())
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'i', 'you', 'he', 'she', 'it'}
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def get_personalized_lesson(self, user_id, language):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_level, total_xp, sections_completed FROM user_progress WHERE user_id=? AND language=?",
            (user_id, language)
        )
        progress = cursor.fetchone()
        
        if not progress:
            level = 'beginner'
        else:
            level, xp, sections = progress
        
        cursor.execute("""
            SELECT word, mastery_level 
            FROM vocabulary 
            WHERE user_id=? AND language=? AND mastery_level < 3
            ORDER BY frequency DESC
            LIMIT 10
        """, (user_id, language))
        weak_words = cursor.fetchall()
        
        cursor.execute(
            "SELECT content FROM lessons WHERE language=? AND level=? LIMIT 1",
            (language, level)
        )
        lesson_data = cursor.fetchone()
        conn.close()
        
        if lesson_data:
            lesson_content = json.loads(lesson_data[0])
            if weak_words:
                lesson_content['focus_words'] = [word[0] for word in weak_words[:5]]
            return lesson_content
        
        return self.generate_adaptive_lesson(user_id, language, level, weak_words)
    
    def generate_adaptive_lesson(self, user_id, language, level, weak_words):
        lesson = {'title': f'Adaptive {level.title()} Lesson', 'type': 'adaptive', 'level': level, 'exercises': []}
        if weak_words:
            lesson['exercises'].append({
                'type': 'vocabulary_review',
                'words': [word[0] for word in weak_words[:5]],
                'instruction': 'Review these words'
            })
        return lesson
    
    def record_performance(self, user_id, language, word, lesson_type, response_time, is_correct, difficulty_level):
        conn = self.get_connection()
        conn.execute("""
            INSERT INTO performance_analytics 
            (user_id, language, word, lesson_type, response_time, is_correct, timestamp, difficulty_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, language, word, lesson_type, response_time, is_correct, datetime.now(), difficulty_level))
        
        if word:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT correct_attempts, incorrect_attempts, mastery_level FROM vocabulary WHERE user_id=? AND word=? AND language=?",
                (user_id, word, language)
            )
            result = cursor.fetchone()
            if result:
                correct, incorrect, mastery = result
                if is_correct:
                    correct += 1
                    if correct > 0 and correct / (correct + incorrect) > 0.8: mastery = min(5, mastery + 1)
                else:
                    incorrect += 1
                    if incorrect > correct: mastery = max(0, mastery - 1)
                
                conn.execute(
                    "UPDATE vocabulary SET correct_attempts=?, incorrect_attempts=?, mastery_level=? WHERE user_id=? AND word=? AND language=?",
                    (correct, incorrect, mastery, user_id, word, language)
                )
        conn.commit()
        conn.close()
        self.update_user_progress(user_id, language, 10 if is_correct else 2)
    
    def update_user_progress(self, user_id, language, xp_earned):
        conn = self.get_connection()
        today = datetime.now().date()
        cursor = conn.cursor()
        cursor.execute("SELECT total_xp, current_level, streak_days, last_activity FROM user_progress WHERE user_id=? AND language=?", (user_id, language))
        result = cursor.fetchone()
        
        if result:
            total_xp, current_level, streak_days, last_activity = result
            new_xp = total_xp + xp_earned
            if last_activity:
                last_date = datetime.strptime(last_activity, '%Y-%m-%d').date() if isinstance(last_activity, str) else last_activity
                if today - last_date == timedelta(days=1): streak_days += 1
                elif today - last_date > timedelta(days=1): streak_days = 1
            else: streak_days = 1
            
            new_level = self.calculate_level(new_xp)
            conn.execute("UPDATE user_progress SET total_xp=?, current_level=?, streak_days=?, last_activity=? WHERE user_id=? AND language=?", 
                         (new_xp, new_level, streak_days, today, user_id, language))
        else:
            conn.execute("INSERT INTO user_progress (user_id, language, total_xp, current_level, streak_days, last_activity) VALUES (?, ?, ?, 'beginner', 1, ?)", 
                         (user_id, language, xp_earned, today))
        conn.commit()
        conn.close()
    
    def calculate_level(self, xp):
        if xp < 100: return 'beginner'
        elif xp < 500: return 'intermediate'
        elif xp < 1500: return 'advanced'
        return 'proficient'
    
    def get_user_stats(self, user_id, language=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        stats = {}
        if language:
            cursor.execute("SELECT total_xp, current_level, streak_days FROM user_progress WHERE user_id=? AND language=?", (user_id, language))
            progress = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE user_id=? AND language=?", (user_id, language))
            vocab_count = cursor.fetchone()[0]
            stats[language] = {'progress': progress, 'vocabulary_size': vocab_count, 'level': progress[1] if progress else 'beginner'}
        else:
            cursor.execute("SELECT language, total_xp, current_level, streak_days FROM user_progress WHERE user_id=?", (user_id,))
            for r in cursor.fetchall():
                stats[r[0]] = {'xp': r[1], 'level': r[2], 'streak': r[3]}
        conn.close()
        return stats
    
    def update_session_stats(self, user_id, language, new_words_count):
        conn = self.get_connection()
        today = datetime.now().date()
        cursor = conn.cursor()
        cursor.execute("SELECT words_learned FROM learning_sessions WHERE user_id=? AND language=? AND session_date=?", (user_id, language, today))
        if cursor.fetchone():
            conn.execute("UPDATE learning_sessions SET words_learned=words_learned+? WHERE user_id=? AND language=? AND session_date=?", (new_words_count, user_id, language, today))
        else:
            conn.execute("INSERT INTO learning_sessions (user_id, language, session_date, words_learned) VALUES (?, ?, ?, ?)", (user_id, language, today, new_words_count))
        conn.commit()
        conn.close()
    
    def get_daily_challenge(self, user_id, language):
        # Simplified logic
        return {'type': 'daily_vocabulary', 'title': 'Learn 3 new words', 'target': 3, 'xp_reward': 30}
    
    def clear_all_adaptive_data(self):
        conn = self.get_connection()
        for table in ['vocabulary', 'oov_words', 'learning_sessions', 'user_progress', 'performance_analytics']:
            try: conn.execute(f"DELETE FROM {table}")
            except: pass
        conn.commit()
        conn.close()
        return True