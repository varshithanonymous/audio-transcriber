"""
Gemini API Service for Word Meanings and Definitions
Uses Google's Gemini AI for comprehensive word information in multiple languages
"""
import google.generativeai as genai
from typing import Dict, Optional
import json

class GeminiWordService:
    """Service to get word meanings using Gemini API"""
    
    def __init__(self, api_key: str):
        """Initialize Gemini API"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("[GEMINI] Using model: gemini-2.5-flash")
        
    def get_word_meaning(self, word: str, language: str = 'en') -> Optional[Dict]:
        """
        Get comprehensive word meaning using Gemini AI
        
        Args:
            word: The word to get meaning for
            language: Language code (en, es, hi)
            
        Returns:
            Dictionary with word information or None
        """
        try:
            # Create language-specific prompt
            language_names = {
                'en': 'English',
                'es': 'Spanish',
                'hi': 'Hindi'
            }
            
            lang_name = language_names.get(language, 'English')
            
            # Simpler prompt that works better
            prompt = f"""Define the {lang_name} word "{word}" in one clear sentence.
Then provide:
- Part of speech
- Example sentence
- 2-3 synonyms

Format as JSON:
{{
  "definition": "your definition here",
  "partOfSpeech": "noun/verb/etc",
  "example": "example sentence",
  "synonyms": ["syn1", "syn2"]
}}"""
            
            print(f"[GEMINI] Requesting meaning for: {word} ({lang_name})")
            
            # Use the API correctly
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            if not response or not response.text:
                print(f"[GEMINI] No response for {word}")
                return None
            
            # Clean the response text
            text = response.text.strip()
            print(f"[GEMINI] Raw response: {text[:150]}...")
            
            # Remove markdown code blocks if present
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            text = text.strip()
            
            # Try to parse JSON
            try:
                word_data = json.loads(text)
                
                formatted = {
                    'word': word,
                    'definition': word_data.get('definition', ''),
                    'partOfSpeech': word_data.get('partOfSpeech', ''),
                    'example': word_data.get('example', ''),
                    'synonyms': word_data.get('synonyms', [])[:5],
                    'translation': '',
                    'pronunciation': '',
                    'source': 'gemini'
                }
                
                print(f"[GEMINI] ✓ Success: {formatted['definition'][:50]}...")
                return formatted
                
            except json.JSONDecodeError:
                # If JSON fails, extract definition from text
                print(f"[GEMINI] JSON parse failed, using text fallback")
                
                # Extract first sentence as definition
                sentences = text.split('.')
                definition = sentences[0].strip() if sentences else text[:150]
                
                return {
                    'word': word,
                    'definition': definition,
                    'partOfSpeech': '',
                    'example': '',
                    'synonyms': [],
                    'translation': '',
                    'pronunciation': '',
                    'source': 'gemini_text'
                }
        
        except Exception as e:
            print(f"[GEMINI] Error for {word} ({language}): {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def validate_word(self, word: str, language: str = 'en') -> bool:
        """Check if a word is valid in the given language"""
        try:
            lang_names = {
                'en': 'English',
                'es': 'Spanish',
                'hi': 'Hindi'
            }
            
            lang_name = lang_names.get(language, 'English')
            
            prompt = f"""
            Is "{word}" a valid {lang_name} word?
            
            Answer with ONLY "YES" or "NO".
            - Answer YES if it's a real word (including slang, informal, or archaic)
            - Answer YES if it's a proper noun
            - Answer NO if it's gibberish, random characters, or not a word
            """
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                answer = response.text.strip().upper()
                return 'YES' in answer
            
            return False
            
        except Exception as e:
            print(f"[GEMINI] Error validating {word}: {e}")
            return False

# Will be initialized in api_service.py
gemini_service = None
