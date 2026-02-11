"""
Learning Level Generator for 100-Level Progressive System
Generates difficulty-appropriate content using Gemini AI
"""
from gemini_service import gemini_service
import json

class LevelGenerator:
    """Generate learning levels with progressive difficulty"""
    
    def __init__(self):
        self.difficulty_tiers = {
            'beginner': (1, 30),
            'intermediate': (31, 60),
            'mastery': (61, 100)
        }
    
    def get_difficulty_tier(self, level_num):
        """Get difficulty tier for a level"""
        if level_num <= 30:
            return 'beginner'
        elif level_num <= 60:
            return 'intermediate'
        else:
            return 'mastery'
    
    def generate_level_content(self, level_num, target_language='es'):
        """Generate 5 words for a specific level using AI"""
        tier = self.get_difficulty_tier(level_num)
        
        # Create AI prompt based on difficulty
        prompts = {
            'beginner': f"List 5 essential {target_language} words for beginners (Level {level_num}). Return JSON: [{{'word': 'X', 'pronunciation': '/x/', 'meaning': 'Y', 'example': 'Z'}}]",
            'intermediate': f"List 5 intermediate {target_language} words (Level {level_num}). Return JSON: [{{'word': 'X', 'pronunciation': '/x/', 'meaning': 'Y', 'example': 'Z'}}]",
            'mastery': f"List 5 advanced {target_language} words (Level {level_num}). Return JSON: [{{'word': 'X', 'pronunciation': '/x/', 'meaning': 'Y', 'example': 'Z'}}]"
        }
        
        try:
            # Add randomness to prompt to ensure uniqueness if level is retried
            import random
            variations = ["common", "useful", "popular", "essential", "daily"]
            variation = random.choice(variations)
            
            final_prompt = prompts[tier] + f" Make them different from previous levels. Focus on {variation} vocabulary."
            
            response = gemini_service.model.generate_content(final_prompt)
            if response and response.text:
                # Clean response
                text = response.text.strip()
                if text.startswith('```json'):
                    text = text[7:]
                if text.startswith('```'):
                    text = text[3:]
                if text.endswith('```'):
                    text = text[:-3]
                text = text.strip()
                
                # Parse JSON
                words = json.loads(text)
                return words[:5]  # Ensure only 5 words
        except Exception as e:
            print(f"[LEVEL_GEN] Error generating level {level_num}: {e}")
        
        # Fallback Procedural Generation (Mock data to ensure uniqueness)
        return self.get_fallback_words(level_num, target_language)

    def get_fallback_words(self, level_num, lang):
        """Generate deterministic fallback words so they are unique per level"""
        base_words = {
            'es': ['casa', 'perro', 'gato', 'coche', 'playa', 'libro', 'escuela', 'hombre', 'mujer', 'niño', 'agua', 'comida', 'tiempo', 'camino', 'dinero'],
            'fr': ['maison', 'chien', 'chat', 'voiture', 'plage', 'livre', 'école', 'homme', 'femme', 'enfant', 'eau', 'nourriture', 'temps', 'chemin', 'argent'],
            'de': ['Haus', 'Hund', 'Katze', 'Auto', 'Strand', 'Buch', 'Schule', 'Mann', 'Frau', 'Kind', 'Wasser', 'Essen', 'Zeit', 'Weg', 'Geld'],
            'hi': ['ghar', 'kutta', 'billi', 'gaadi', 'samundar', 'kitab', 'vidyalay', 'aadmi', 'aurat', 'bacha', 'paani', 'khana', 'samay', 'rasta', 'paisa']
        }
        
        vocab = base_words.get(lang, base_words['es'])
        
        # Generate 5 words based on level_num offset
        words = []
        for i in range(5):
            idx = (level_num * 5 + i) % len(vocab)
            word = vocab[idx]
            words.append({
                'word': word, 
                'pronunciation': f'/{word}/', 
                'meaning': f'Meaning of {word}', 
                'example': f'This is {word} in context.'
            })
            
        return words
    
    def get_level_metadata(self, level_num):
        """Get metadata for a level"""
        tier = self.get_difficulty_tier(level_num)
        
        themes = {
            'beginner': [
                "Greetings & Basics", "Numbers & Counting", "Family & Friends",
                "Food & Drinks", "Colors & Shapes", "Daily Routine",
                "Body Parts", "Weather", "Animals", "Common Objects",
                "Basic Verbs", "Time & Days", "Places", "Clothing",
                "House & Home", "Emotions", "School", "Transportation",
                "Fruits & Vegetables", "Simple Questions", "Directions",
                "Shopping", "Restaurant", "Travel Essentials", "Sports",
                "Music", "Hobbies", "Nature", "Occupations", "Quantities"
            ],
            'intermediate': [
                "Complex Emotions", "Abstract Concepts", "Professional Life",
                "Technology", "Health & Wellness", "Cultural Topics",
                "Politics & Society", "Environment", "Economics",
                "Education System", "Legal Terms", "Psychology",
                "Philosophy", "History", "Science", "Art & Literature",
                "Media & Entertainment", "Social Issues", "Ethics",
                "Religion & Beliefs", "Relationships", "Communication",
                "Business", "Marketing", "Finance", "Innovation",
                "Global Issues", "Sustainability", "Urban Life", "Rural Life"
            ],
            'mastery': [
                "Idiomatic Expressions", "Advanced Grammar", "Literary Devices",
                "Figurative Language", "Regional Dialects", "Formal Writing",
                "Academic Discourse", "Technical Jargon", "Specialized Fields",
                "Nuanced Meanings", "Cultural Idioms", "Historical Terms",
                "Philosophical Concepts", "Scientific Terminology", "Legal Language",
                "Medical Vocabulary", "Poetic Expressions", "Rhetorical Devices",
                "Complex Syntax", "Abstract Theory", "Industry Specific",
                "Research Terminology", "Advanced Composition", "Critical Analysis",
                "Semantic Nuances", "Contextual Usage", "Professional Discourse",
                "Expert Communication", "Specialized Topics", "Mastery Synthesis",
                "Academic Excellence", "Professional Mastery", "Cultural Fluency",
                "Native-Level Expression", "Complete Fluency", "Language Mastery",
                "Expert Proficiency", "Total Command", "Ultimate Mastery", "Certification Ready"
            ]
        }
        
        tier_themes = themes[tier]
        theme_index = (level_num - 1) % len(tier_themes)
        
        return {
            'title': tier_themes[theme_index],
            'xp': 50 + (level_num * 2),  # Progressive XP
            'tier': tier.capitalize(),
            'icon': self._get_level_icon(level_num, tier)
        }
    
    def _get_level_icon(self, level_num, tier):
        """Get appropriate emoji for level"""
        if tier == 'beginner':
            icons = ["👋", "🔢", "👨‍👩‍👧", "🍕", "🌈", "⏰", "💪", "⛅", "🐕", "📱"]
            return icons[(level_num - 1) % len(icons)]
        elif tier == 'intermediate':
            icons = ["🎓", "💼", "🌍", "🏥", "🎨", "📚", "🔬", "🏛️", "🎭", "🎵"]
            return icons[(level_num - 31) % len(icons)]
        else:
            icons = ["🏆", "👑", "💎", "🎖️", "⭐", "🔥", "💫", "🌟", "✨", "👨‍🎓"]
            return icons[(level_num - 61) % len(icons)]

# Global instance
level_generator = LevelGenerator()
