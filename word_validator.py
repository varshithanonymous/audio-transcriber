import sqlite3
import requests
import json
import time
from threading import Lock
from database_manager import db
from api_service import api_service

class WordValidator:
    def __init__(self):
        self.lock = Lock()
    
    def is_online(self):
        return api_service.is_online()
    
    def get_word_meaning(self, word, language):
        """Get enhanced word information using the API service"""
        if not self.is_online():
            return None
        
        try:
            # Use the enhanced API service
            word_info = api_service.get_enhanced_word_info(word, language)
            
            if word_info and word_info.get('definition'):
                # Format a rich meaning string
                parts = []
                
                # Main definition
                parts.append(word_info['definition'])
                
                # Add phonetic if available
                if word_info.get('phonetic'):
                    parts[0] = f"({word_info['phonetic']}) " + parts[0]
                
                # Add example if available
                if word_info.get('examples'):
                    parts.append(f"Example: {word_info['examples'][0]}")
                
                # Add synonyms if available
                if word_info.get('synonyms'):
                    syn_list = ', '.join(word_info['synonyms'][:5])
                    parts.append(f"Synonyms: {syn_list}")
                
                return ' | '.join(parts)
            
            return None
            
        except Exception as e:
            print(f"[VALIDATOR] Error fetching meaning for {word} ({language}): {e}")
            return None

    
    def validate_and_store_word(self, user_id, word, language):
        with self.lock:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check existing
            cursor.execute(
                "SELECT meaning, is_valid FROM vocabulary WHERE user_id=? AND word=? AND language=?",
                (user_id, word.lower(), language)
            )
            result = cursor.fetchone()
            
            # If found and has a meaning, OR if we are still offline and can't improve it, return cached
            if result and (result[0] or not self.is_online()):
                conn.close()
                return {'cached': True, 'meaning': result[0], 'is_valid': bool(result[1])}
            
            # If we are here, either it's new, OR it's existing but missing meaning and we are online.
            # Helper: Validate online
            meaning = self.get_word_meaning(word, language)
            is_valid = meaning is not None
            
            # If we failed to get meaning again (different kind of failure?), keep old if exists? 
            # But here we just update/insert.
            
            # Store Result (Using 'vocabulary' table)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                if result:
                    # UPDATE existing - preserve frequency, mastery
                    cursor.execute(
                        "UPDATE vocabulary SET meaning=?, is_valid=?, last_practiced=? WHERE user_id=? AND word=? AND language=?",
                        (meaning or '', int(is_valid), timestamp, user_id, word.lower(), language)
                    )
                    print(f"[VALIDATOR] Updated: {word} ({language}) - {meaning[:50] if meaning else 'No meaning'}", flush=True)
                else:
                    # INSERT new
                    cursor.execute(
                        """INSERT INTO vocabulary 
                           (user_id, word, language, meaning, is_valid, first_seen, last_practiced) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, word.lower(), language, meaning or '', int(is_valid), timestamp, timestamp)
                    )
                    print(f"[VALIDATOR] Inserted: {word} ({language}) - {meaning[:50] if meaning else 'No meaning'}", flush=True)
                conn.commit()
            except Exception as e:
                print(f"DB Error in validator: {e}", flush=True)
            finally:
                conn.close()
            
            return {'cached': False, 'meaning': meaning, 'is_valid': is_valid}
    
    def get_user_words(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """SELECT word, language, meaning, is_valid, last_practiced, source_context, 
                          frequency, mastery_level 
                   FROM vocabulary WHERE user_id=?"""
        params = [user_id]
        
        if language:
            query += " AND language=?"
            params.append(language)
            
        query += " ORDER BY last_practiced DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'word': r[0], 
            'language': r[1], 
            'meaning': r[2], 
            'is_valid': bool(r[3]), 
            'timestamp': r[4], 
            'source': r[5],
            'frequency': r[6] or 1,
            'mastery_level': r[7] or 0
        } for r in results]
