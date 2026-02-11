"""
Conversation Engine for LinguaVoice
Handles rule-based chat interactions, grammar checking, and language practice logic.
"""
import random
from api_service import api_service

class ConversationEngine:
    def __init__(self):
        # Common patterns for different languages
        self.patterns = {
            'en': {
                'greetings': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
                'how_are_you': ['how are you', 'how are things', 'how is it going'],
                'introductions': ['my name is', 'i am', 'call me'],
                'help': ['help', 'what can you do', 'how does this work'],
                'goodbye': ['bye', 'goodbye', 'see you', 'later']
            },
            'es': {
                'greetings': ['hola', 'buenos días', 'buenas tardes', 'buenas noches'],
                'how_are_you': ['cómo estás', 'qué tal', 'cómo va'],
                'introductions': ['mi nombre es', 'me llamo', 'soy'],
                'help': ['ayuda', 'qué puedes hacer', 'cómo funciona'],
                'goodbye': ['adiós', 'hasta luego', 'nos vemos', 'chao']
            },
            'hi': {
                'greetings': ['namaste', 'namashkar', 'hello', 'hi'],
                'how_are_you': ['aap kaise hain', 'kya haal hai', 'sab theek hai'],
                'introductions': ['mera naam', 'main hoon'],
                'help': ['madad', 'sahayata'],
                'goodbye': ['alvida', 'phir milenge', 'bye']
            }
        }
        
        self.responses = {
            'en': {
                'greeting': ["Hello! Ready to practice English?", "Hi there! What would you like to talk about?", "Greetings! I'm listening."],
                'how_are_you': ["I'm just a computer program, but I'm functioning perfectly! How are you?", "Doing great! Ready to help you learn."],
                'intro': ["Nice to meet you! I am your AI language tutor.", "Pleasure to meet you. Let's practice!"],
                'help': ["I can help you practice speaking. Just say something, and I'll check your grammar and respond!", "I listen to your pronunciation and help with vocabulary."],
                'goodbye': ["Goodbye! Keep practicing!", "See you next time!", "Have a great day!"],
                'fallback': ["That's interesting! Tell me more.", "I see. Can you elaborate?", "Good job speaking! Try saying that in a different way.", "I'm listening. Go on."]
            },
            'es': {
                'greeting': ["¡Hola! ¿Listo para practicar español?", "¡Buenas! ¿De qué te gustaría hablar?", "¡Saludos! Estoy escuchando."],
                'how_are_you': ["Soy un programa, ¡pero funciono perfectamente! ¿Y tú?", "¡Todo bien! Listo para ayudarte a aprender."],
                'intro': ["¡Mucho gusto! Soy tu tutor de idiomas IA.", "Encantado. ¡Practiquemos!"],
                'help': ["Puedo ayudarte a practicar. ¡Solo di algo y revisaré tu gramática!", "Escucho tu pronunciación y te ayudo con el vocabulario."],
                'goodbye': ["¡Adiós! ¡Sigue practicando!", "¡Hasta la próxima!", "¡Que tengas un buen día!"],
                'fallback': ["¡Qué interesante! Cuéntame más.", "Ya veo. ¿Puedes explicarme más?", "¡Buen trabajo! Intenta decirlo de otra manera.", "Te escucho. Continúa."]
            },
            'hi': {
                'greeting': ["Namaste! Hindi abhyas ke liye taiyaar?", "Hello! Aaj hum kya baat karenge?", "Namashkar! Main sun raha hoon."],
                'how_are_you': ["Main theek hoon! Aap kaise hain?", "Sab badiya! Main aapki madat ke liye taiyaar hoon."],
                'intro': ["Aapse milkar khushi hui! Main aapka AI tutor hoon.", "Namaste. Chaliye abhyas karte hain!"],
                'help': ["Main aapki bolne mein madad kar sakta hoon. Kuch boliye!", "Main aapki vocabulary aur grammar check karunga."],
                'goodbye': ["Alvida! Abhyas karte rahein!", "Phir milenge!", "Shubh din!"],
                'fallback': ["Yeh dilchasp hai! Aur batayein.", "Samjha. Kya aap vistār mein bata sakte hain?", "Bahut badhiya! Ise kisi aur tarah se kahne ki koshish karein.", "Main sun raha hoon."]
            }
        }

    def get_response(self, user_text: str, language: str = 'en') -> dict:
        """
        Generate a response based on user input and checking grammar
        """
        if not user_text:
            return {'response': '', 'correction': None}
            
        language = language.lower()
        if language not in self.patterns:
            language = 'en'
            
        # 1. Grammar Check
        grammar_result = api_service.check_grammar(user_text, language)
        correction = None
        
        # Only suggest correction if there's a significant error and it's 
        # not just a proper noun issue
        if grammar_result['error_count'] > 0:
            if grammar_result['corrected_text'] != user_text:
                correction = {
                    'original': user_text,
                    'corrected': grammar_result['corrected_text'],
                    'message': "I noticed a small grammar improvement:"
                }

        # 2. Determine Intent & Response
        text_lower = user_text.lower()
        response_text = ""
        
        lang_patterns = self.patterns[language]
        lang_responses = self.responses[language]
        
        # Check patterns
        if any(p in text_lower for p in lang_patterns.get('greetings', [])):
            response_text = random.choice(lang_responses['greeting'])
        elif any(p in text_lower for p in lang_patterns.get('how_are_you', [])):
            response_text = random.choice(lang_responses['how_are_you'])
        elif any(p in text_lower for p in lang_patterns.get('introductions', [])):
            response_text = random.choice(lang_responses['intro'])
        elif any(p in text_lower for p in lang_patterns.get('help', [])):
            response_text = random.choice(lang_responses['help'])
        elif any(p in text_lower for p in lang_patterns.get('goodbye', [])):
            response_text = random.choice(lang_responses['goodbye'])
        else:
            # Fallback for general conversation
            response_text = random.choice(lang_responses['fallback'])
            
            # If we have a correction, maybe acknowledge it in the response logic?
            # For now, keeping them separate is cleaner.

        return {
            'response': response_text,
            'correction': correction,
            'language': language
        }

# Global instance
conversation_engine = ConversationEngine()
