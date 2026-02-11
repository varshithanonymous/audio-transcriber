"""
Enhanced API Service Layer for LinguaVoice
Integrates Free Dictionary API, Datamuse API, and LanguageTool API
"""
import requests
import json
from typing import Dict, List, Optional
from functools import lru_cache
import time

class APIService:
    """Centralized API service for all external API calls"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LinguaVoice/1.0 (Educational Language Learning App)'
        })
        self.timeout = 5
        self.cache = {}
    
    def is_online(self) -> bool:
        """Check if internet connection is available"""
        try:
            requests.get("https://httpbin.org/status/200", timeout=2)
            return True
        except:
            return False
    
    # ==================== FREE DICTIONARY API ====================
    
    def get_word_definition(self, word: str, language: str = 'en') -> Optional[Dict]:
        """
        Get word definition from Free Dictionary API
        Returns: {
            'word': str,
            'phonetic': str,
            'definitions': List[Dict],
            'synonyms': List[str],
            'antonyms': List[str]
        }
        """
        if not self.is_online():
            return None
        
        # Create cache key
        cache_key = f"def_{language}_{word.lower()}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Free Dictionary API supports multiple languages
            lang_codes = {
                'en': 'en',
                'es': 'es',
                'fr': 'fr',
                'de': 'de',
                'hi': 'hi'
            }
            
            lang_code = lang_codes.get(language, 'en')
            url = f"https://api.dictionaryapi.dev/api/v2/entries/{lang_code}/{word.lower()}"
            
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    entry = data[0]
                    
                    # Extract all definitions
                    all_definitions = []
                    all_synonyms = set()
                    all_antonyms = set()
                    
                    for meaning in entry.get('meanings', []):
                        part_of_speech = meaning.get('partOfSpeech', '')
                        
                        for definition in meaning.get('definitions', []):
                            all_definitions.append({
                                'definition': definition.get('definition', ''),
                                'example': definition.get('example', ''),
                                'partOfSpeech': part_of_speech
                            })
                            
                            # Collect synonyms and antonyms
                            all_synonyms.update(definition.get('synonyms', []))
                            all_antonyms.update(definition.get('antonyms', []))
                    
                    result = {
                        'word': entry.get('word', word),
                        'phonetic': entry.get('phonetic', ''),
                        'audio': entry.get('phonetics', [{}])[0].get('audio', ''),
                        'definitions': all_definitions[:5],  # Limit to top 5
                        'synonyms': list(all_synonyms)[:10],
                        'antonyms': list(all_antonyms)[:10]
                    }
                    
                    # Cache the result
                    self.cache[cache_key] = result
                    return result
            
            return None
            
        except Exception as e:
            print(f"[API_SERVICE] Error fetching definition for {word}: {e}")
            return None
    
    # ==================== DATAMUSE API ====================
    
    def get_similar_words(self, word: str, max_results: int = 10) -> List[str]:
        """
        Get similar/related words using Datamuse API
        Great for vocabulary building
        """
        if not self.is_online():
            return []
        
        cache_key = f"similar_{word.lower()}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Datamuse API - words with similar meaning
            url = f"https://api.datamuse.com/words?ml={word}&max={max_results}"
            
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                similar_words = [item['word'] for item in data if 'word' in item]
                
                self.cache[cache_key] = similar_words
                return similar_words
            
            return []
            
        except Exception as e:
            print(f"[API_SERVICE] Error fetching similar words for {word}: {e}")
            return []
    
    def get_rhyming_words(self, word: str, max_results: int = 10) -> List[str]:
        """Get rhyming words - useful for creative learning"""
        if not self.is_online():
            return []
        
        try:
            url = f"https://api.datamuse.com/words?rel_rhy={word}&max={max_results}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return [item['word'] for item in data if 'word' in item]
            
            return []
            
        except Exception as e:
            print(f"[API_SERVICE] Error fetching rhymes for {word}: {e}")
            return []
    
    def get_word_suggestions(self, prefix: str, max_results: int = 10) -> List[str]:
        """Get word suggestions based on prefix - for autocomplete"""
        if not self.is_online():
            return []
        
        try:
            url = f"https://api.datamuse.com/sug?s={prefix}&max={max_results}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return [item['word'] for item in data if 'word' in item]
            
            return []
            
        except Exception as e:
            print(f"[API_SERVICE] Error fetching suggestions for {prefix}: {e}")
            return []
    
    # ==================== LANGUAGETOOL API ====================
    
    def check_grammar(self, text: str, language: str = 'en-US') -> Dict:
        """
        Check grammar using LanguageTool API
        Returns: {
            'matches': List[Dict],  # Grammar errors/suggestions
            'corrected_text': str
        }
        """
        if not self.is_online() or not text:
            return {'matches': [], 'corrected_text': text}
        
        try:
            # LanguageTool public API
            url = "https://api.languagetool.org/v2/check"
            
            # Map language codes
            lang_map = {
                'en': 'en-US',
                'es': 'es',
                'hi': 'en-US',  # Hindi not supported, fallback to English
                'fr': 'fr',
                'de': 'de-DE'
            }
            
            lang_code = lang_map.get(language, 'en-US')
            
            data = {
                'text': text,
                'language': lang_code
            }
            
            response = self.session.post(url, data=data, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                matches = result.get('matches', [])
                
                # Format matches
                formatted_matches = []
                for match in matches:
                    formatted_matches.append({
                        'message': match.get('message', ''),
                        'shortMessage': match.get('shortMessage', ''),
                        'offset': match.get('offset', 0),
                        'length': match.get('length', 0),
                        'replacements': [r.get('value', '') for r in match.get('replacements', [])[:3]],
                        'rule': match.get('rule', {}).get('category', {}).get('name', 'Grammar')
                    })
                
                # Generate corrected text
                corrected = text
                # Apply corrections in reverse order to maintain offsets
                for match in sorted(matches, key=lambda x: x.get('offset', 0), reverse=True):
                    replacements = match.get('replacements', [])
                    if replacements:
                        offset = match['offset']
                        length = match['length']
                        replacement = replacements[0]['value']
                        corrected = corrected[:offset] + replacement + corrected[offset + length:]
                
                return {
                    'matches': formatted_matches,
                    'corrected_text': corrected,
                    'error_count': len(formatted_matches)
                }
            
            return {'matches': [], 'corrected_text': text, 'error_count': 0}
            
        except Exception as e:
            print(f"[API_SERVICE] Error checking grammar: {e}")
            return {'matches': [], 'corrected_text': text, 'error_count': 0}
    
    def get_enhanced_word_info(self, word: str, language: str = 'en') -> Dict:
        """
        Get comprehensive word information combining multiple APIs
        Priority: Gemini API > Free Dictionary API > Offline Dictionary > Fallback
        """
        result = {
            'word': word,
            'language': language,
            'definition': None,
            'phonetic': None,
            'audio': None,
            'examples': [],
            'synonyms': [],
            'antonyms': [],
            'similar_words': [],
            'source': 'offline'
        }
        
        if not self.is_online():
            return result
        
        # Try Gemini API first (best for all languages)
        try:
            from gemini_service import gemini_service
            if gemini_service:
                gemini_result = gemini_service.get_word_meaning(word, language)
                if gemini_result and gemini_result.get('definition'):
                    result['definition'] = gemini_result['definition']
                    result['phonetic'] = gemini_result.get('pronunciation', '')
                    result['examples'] = [gemini_result.get('example', '')] if gemini_result.get('example') else []
                    result['synonyms'] = gemini_result.get('synonyms', [])
                    result['source'] = 'gemini'
                    
                    print(f"[API_SERVICE] Got meaning from Gemini for {word} ({language}): {result['definition'][:50]}...")
                    return result
        except Exception as e:
            print(f"[API_SERVICE] Gemini error for {word}: {e}")
        
        # Fallback to Free Dictionary API (mainly for English)
        if language == 'en':
            definition_data = self.get_word_definition(word, language)
            if definition_data and definition_data.get('definitions'):
                result['definition'] = definition_data['definitions'][0]['definition']
                result['phonetic'] = definition_data.get('phonetic', '')
                result['audio'] = definition_data.get('audio', '')
                result['examples'] = [d['example'] for d in definition_data['definitions'] if d.get('example')][:3]
                result['synonyms'] = definition_data.get('synonyms', [])
                result['antonyms'] = definition_data.get('antonyms', [])
                result['source'] = 'dictionary_api'
                return result
        
        # Try offline dictionary for Spanish and Hindi
        if language in ['es', 'hi']:
            try:
                from offline_dictionary import offline_dict
                offline_result = offline_dict.get_definition(word, language)
                if offline_result:
                    result['definition'] = offline_result['definition']
                    result['source'] = 'offline_dictionary'
                    print(f"[API_SERVICE] Got meaning from offline dict for {word} ({language})")
                    return result
            except Exception as e:
                print(f"[API_SERVICE] Offline dict error: {e}")
        
        # Final fallback message
        fallback_messages = {
            'en': "Definition pending...",
            'es': "Definición pendiente...",
            'hi': "परिभाषा लंबित..."
        }
        
        if not result['definition']:
            result['definition'] = fallback_messages.get(language, "Definition pending...")
            result['source'] = 'fallback'
        
        return result

# Global instance
api_service = APIService()
