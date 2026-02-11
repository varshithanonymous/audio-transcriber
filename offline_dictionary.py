"""
Offline Dictionary Service
Provides word definitions for Spanish and Hindi when API is unavailable
"""
import json
import os

class OfflineDictionary:
    """Offline dictionary with Spanish and Hindi words"""
    
    def __init__(self):
        self.dictionaries = {}
        self.load_dictionaries()
    
    def load_dictionaries(self):
        """Load dictionary JSON files"""
        dict_dir = os.path.join(os.path.dirname(__file__), 'dictionaries')
        
        # Load Spanish dictionary
        try:
            with open(os.path.join(dict_dir, 'spanish_dict.json'), 'r', encoding='utf-8') as f:
                self.dictionaries['es'] = json.load(f)
            print(f"[OFFLINE_DICT] Loaded {len(self.dictionaries['es'])} Spanish words")
        except Exception as e:
            print(f"[OFFLINE_DICT] Error loading Spanish dict: {e}")
            self.dictionaries['es'] = {}
        
        # Load Hindi dictionary
        try:
            with open(os.path.join(dict_dir, 'hindi_dict.json'), 'r', encoding='utf-8') as f:
                self.dictionaries['hi'] = json.load(f)
            print(f"[OFFLINE_DICT] Loaded {len(self.dictionaries['hi'])} Hindi words")
        except Exception as e:
            print(f"[OFFLINE_DICT] Error loading Hindi dict: {e}")
            self.dictionaries['hi'] = {}
    
    def get_definition(self, word: str, language: str = 'en'):
        """Get word definition from offline dictionary"""
        if language not in ['es', 'hi']:
            return None
        
        # Normalize word (lowercase)
        word_lower = word.lower().strip()
        
        # Check if word exists in dictionary
        if word_lower in self.dictionaries.get(language, {}):
            definition = self.dictionaries[language][word_lower]
            print(f"[OFFLINE_DICT] ✓ Found {word} ({language}): {definition[:50]}...")
            return {
                'word': word,
                'definition': definition,
                'source': 'offline_dictionary'
            }
        
        return None

# Global instance
offline_dict = OfflineDictionary()
