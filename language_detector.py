import re
from collections import Counter

class OfflineLanguageDetector:
    def __init__(self):
        # Language patterns for basic detection
        self.patterns = {
            'en': {
                'chars': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                'common_words': {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with', 'for', 'as', 'was', 'on', 'are', 'you', 'this', 'be', 'at', 'have'}
            },
            'es': {
                'chars': set('abcdefghijklmnopqrstuvwxyzáéíóúüñABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'),
                'common_words': {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para'}
            },
            'hi': {
                'chars': set('अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञ'),
                'common_words': {'है', 'का', 'की', 'के', 'में', 'से', 'को', 'और', 'यह', 'वह', 'पर', 'एक', 'हो', 'गया', 'था', 'कि', 'जो', 'तो', 'ही', 'या'}
            }
        }
    
    def detect_language(self, text):
        if not text.strip():
            return 'unknown'
        
        scores = {'en': 0, 'es': 0, 'hi': 0}
        words = text.lower().split()
        
        # Character-based scoring
        for lang, data in self.patterns.items():
            char_score = sum(1 for char in text if char in data['chars'])
            scores[lang] += char_score / len(text) * 50
            
            # Word-based scoring
            word_score = sum(1 for word in words if word in data['common_words'])
            scores[lang] += word_score / len(words) * 50 if words else 0
        
        detected = max(scores, key=scores.get)
        return detected if scores[detected] > 10 else 'unknown'