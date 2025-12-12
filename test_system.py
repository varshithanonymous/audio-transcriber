from language_detector import OfflineLanguageDetector
from word_validator import WordValidator

# Test the offline language detection and word validation system
print("Initializing systems...")
detector = OfflineLanguageDetector()
validator = WordValidator()
print("Systems initialized successfully!\n")

# Test language detection
test_texts = [
    "Hello how are you today",
    "Hola como estas hoy", 
    "aaj aap kaise hain",
    "The quick brown fox jumps"
]

print("Testing Offline Language Detection:")
for text in test_texts:
    lang = detector.detect_language(text)
    print(f"'{text}' -> {lang}")

print("\nTesting Word Validation:")
# Test word validation
test_words = [
    ("hello", "en"),
    ("world", "en"), 
    ("hola", "es"),
    ("mundo", "es")
]

for word, lang in test_words:
    result = validator.validate_and_store_word("test_user", word, lang)
    print(f"Word: {word} ({lang}) -> Valid: {result['is_valid']}, Meaning: {result.get('meaning', 'N/A')}")

print("\nUser's Validated Words:")
user_words = validator.get_user_words("test_user")
for word_data in user_words:
    print(f"{word_data['word']} ({word_data['language']}) - {word_data['meaning']}")

print("\nSystem working! Ready for integration with audio transcription.")