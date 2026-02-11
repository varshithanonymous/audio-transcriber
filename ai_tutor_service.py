"""
AI Tutor Chat API using Gemini 2.5 Flash
"""
from gemini_service import gemini_service

def get_ai_tutor_response(message, base_language, target_language, history):
    """Get AI tutor response using Gemini"""
    
    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'hi': 'Hindi'
    }
    
    base_lang_name = language_names.get(base_language, 'English')
    target_lang_name = language_names.get(target_language, 'Spanish')
    
    # Build context from history
    context = ""
    if history:
        for exchange in history[-5:]:  # Last 5 exchanges
            context += f"Student: {exchange['user']}\nTutor: {exchange['ai']}\n"
    
    # Create tutor prompt
    prompt = f"""You are not just a tutor, but a close, supportive friend who is helping me learn {target_lang_name}. 
Your student speaks {base_lang_name} and is excited to learn from you!

Personality Guidelines:
- Be warm, conversational, and use friendly language (like "Hey there!", "You're doing great!", "Don't worry, I've got your back!").
- Keep responses encouraging and lighthearted.
- Use {target_lang_name} naturally in conversation, but always provide the {base_lang_name} translation so I can follow along.
- If I make a mistake, gently point it out as a "learning moment" between friends.
- Ask questions that a friend would ask to keep the conversation flowing.

Previous conversation:
{context}

Friend's message: {message}

Respond as a warm, interactive friend. Keep it natural and engaging."""

    try:
        response = gemini_service.model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[AI_TUTOR] Error: {e}")
    
    return "Hey! I'm having a little glitch in my system. Let's try again in a moment, friend!"

def get_note_translation(text, target_language):
    """Translate a recorded note into English and provide explanation"""
    
    prompt = f"""Translate the following text from {target_language} to English. 
Provide a clear translation and a brief, friendly explanation of any interesting words or grammar points.

Text: {text}

Return JSON format:
{{
  "translation": "English translation",
  "explanation": "Brief friendly explanation",
  "original": "{text}"
}}"""

    try:
        response = gemini_service.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response and response.text:
            text_res = response.text.strip()
            if text_res.startswith('```json'): text_res = text_res[7:]
            if text_res.endswith('```'): text_res = text_res[:-3]
            
            import json
            return json.loads(text_res.strip())
    except Exception as e:
        print(f"[NOTES_TRANS] Error: {e}")
    
    return {
        "translation": "Could not translate right now.",
        "explanation": "Translation service is temporarily unavailable.",
        "original": text
    }

def get_practice_phrase(base_language, target_language):
    """Get a practice phrase for voice conversation"""
    
    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'hi': 'Hindi'
    }
    
    target_lang_name = language_names.get(target_language, 'Spanish')
    base_lang_name = language_names.get(base_language, 'English')
    
    prompt = f"""Generate a simple, common {target_lang_name} phrase for a beginner to practice speaking.
Make it practical and useful for everyday conversation.

Return JSON format:
{{
  "phrase": "the {target_lang_name} phrase",
  "translation": "{base_lang_name} translation",
  "context": "when to use this phrase"
}}

Example for Spanish:
{{
  "phrase": "¿Cómo estás?",
  "translation": "How are you?",
  "context": "Greeting someone you know"
}}"""

    try:
        response = gemini_service.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response and response.text:
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            import json
            return json.loads(text)
    except Exception as e:
        print(f"[AI_TUTOR] Phrase error: {e}")
    
    # Fallback
    return {
        "phrase": "Hola",
        "translation": "Hello",
        "context": "Basic greeting"
    }

def check_pronunciation(expected, actual, language):
    """Check if user's speech matches expected phrase"""
    
    # Simple similarity check (can be enhanced)
    expected_lower = expected.lower().strip()
    actual_lower = actual.lower().strip()
    
    # Calculate similarity
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, expected_lower, actual_lower).ratio()
    
    if similarity > 0.7:
        return {
            "correct": True,
            "message": "Excellent! Perfect pronunciation! 🎉",
            "similarity": similarity
        }
    elif similarity > 0.4:
        return {
            "correct": False,
            "message": f"Almost there! Try again. Expected: '{expected}'",
            "similarity": similarity
        }
    else:
        return {
            "correct": False,
            "message": f"Let's try again. Listen carefully and repeat: '{expected}'",
            "similarity": similarity
        }

def generate_quiz_questions(level_id, tier='beginner', target_language='es', words=None):
    """Generate 5 quiz questions for a specific level using Gemini"""
    
    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'hi': 'Hindi'
    }
    
    lang_name = language_names.get(target_language, 'Spanish')
    
    # If words are provided, build a specific prompt
    if words:
        # Extract word list
        word_list = [w.get('word', '') for w in words]
        word_list_str = ", ".join(word_list)
        
        prompt = f"""Generate 5 multiple-choice quiz questions using these specific {lang_name} words: {word_list_str}.
Each question should test one of these words.
Level {level_id}.

Return ONLY a JSON array:
[
  {{
    "type": "multiple_choice",
    "question": "What does 'XXXX' mean?",
    "word": "XXXX",
    "options": ["Option1", "Option2", "Option3", "Option4"],
    "correct": "CorrectOption",
    "language": "{target_language}"
  }}
]"""
    else:
        # Fallback to general generation if no words provided
        prompt = f"""Generate 5 simple {lang_name} quiz questions for absolute beginners (Level {level_id}).... (fallback logic)"""
        # Reusing existing prompt logic structure but simplifying for the 'else' block or just using standard logic
        
        # To avoid duplicating too much, let's just stick to the dictionary for general cases
        prompts = {
            'beginner': f"""Generate 5 simple {lang_name} quiz questions for absolute beginners (Level {level_id}).
Focus on basic vocabulary like greetings, numbers, food, family.

Return ONLY a JSON array:
[
  {{
    "type": "multiple_choice",
    "question": "What does 'hola' mean?",
    "word": "hola",
    "options": ["Hello", "Goodbye", "Please", "Thank you"],
    "correct": "Hello",
    "language": "{target_language}"
  }}
]""",
            'intermediate': f"""Generate 5 intermediate {lang_name} quiz questions (Level {level_id}). Focus on descriptive words... Return same JSON format.""",
            'mastery': f"""Generate 5 advanced {lang_name} quiz questions (Level {level_id}). Focus on complex vocabulary... Return same JSON format."""
        }
        prompt = prompts.get(tier, prompts['beginner'])

    try:
        response = gemini_service.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response and response.text:
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            import json
            questions = json.loads(text)
            # Ensure correct language tag
            for q in questions:
                q['language'] = target_language
            return questions[:5]  # Ensure only 5 questions
    except Exception as e:
        print(f"[QUIZ_GEN] Error: {e}")
    
    # Fallback Procedural
    return get_fallback_quiz(level_id, target_language, words)

def get_fallback_quiz(level_id, lang, words=None):
    """Generate deterministic fallback quiz"""
    
    # If words are provided, generate quiz from them
    if words and len(words) >= 4:
        questions = []
        all_meanings = [w.get('meaning', 'Unknown') for w in words]
        
        import random
        
        for w in words:
            word_str = w.get('word', '')
            correct_meaning = w.get('meaning', 'Unknown')
            
            # Pick distractors from other words
            distractors = [m for m in all_meanings if m != correct_meaning]
            if len(distractors) < 3:
                distractors += ["Option A", "Option B", "Option C"] # Ensure enough
            
            random.shuffle(distractors)
            opts = [correct_meaning] + distractors[:3]
            random.shuffle(opts)
            
            questions.append({
                "type": "multiple_choice", 
                "question": f"What does '{word_str}' mean?", 
                "word": word_str, 
                "options": opts, 
                "correct": correct_meaning, 
                "language": lang
            })
        return questions[:5]

    base_data = {
        'es': [
            {"q": "What is 'House'?", "w": "Casa", "o": ["Casa", "Perro", "Gato", "Agua"], "c": "Casa"},
            {"q": "Translate 'Hello'", "w": "Hola", "o": ["Hola", "Adiós", "Gracias", "Por favor"], "c": "Hola"},
            {"q": "What is 'Cat'?", "w": "Gato", "o": ["Gato", "Perro", "Casa", "Coche"], "c": "Gato"},
            {"q": "Translate 'Water'", "w": "Agua", "o": ["Agua", "Comida", "Aire", "Fuego"], "c": "Agua"},
            {"q": "What is 'Friend'?", "w": "Amigo", "o": ["Amigo", "Enemigo", "Padre", "Madre"], "c": "Amigo"}
        ],
        'fr': [
            {"q": "What is 'House'?", "w": "Maison", "o": ["Maison", "Chien", "Chat", "Eau"], "c": "Maison"},
            {"q": "Translate 'Hello'", "w": "Bonjour", "o": ["Bonjour", "Au revoir", "Merci", "S'il vous plaît"], "c": "Bonjour"},
            {"q": "What is 'Cat'?", "w": "Chat", "o": ["Chat", "Chien", "Maison", "Voiture"], "c": "Chat"},
            {"q": "Translate 'Water'", "w": "Eau", "o": ["Eau", "Nourriture", "Air", "Feu"], "c": "Eau"},
            {"q": "What is 'Friend'?", "w": "Ami", "o": ["Ami", "Ennemi", "Père", "Mère"], "c": "Ami"}
        ],
        # Add others as needed, default to ES
    }
    
    data = base_data.get(lang, base_data['es'])
    questions = []
    
    # Procedurally generate slightly different questions per level if possible, 
    # but for now just rotate the mapping or use static list
    # To avoid "same every level", we can rotate based on level_id
    
    for i in range(5):
        item = data[(level_id + i) % len(data)]
        questions.append({
            "type": "multiple_choice", 
            "question": f"{item['q']} (L{level_id})", # Add level to visual to prove it changes
            "word": item['w'], 
            "options": item['o'], 
            "correct": item['c'], 
            "language": lang
        })
        
    return questions
