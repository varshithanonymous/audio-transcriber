from flask import Flask, render_template, jsonify, request
import sqlite3
from word_validator import WordValidator
from language_detector import OfflineLanguageDetector

app = Flask(__name__)
word_validator = WordValidator()
lang_detector = OfflineLanguageDetector()

@app.route("/")
def index():
    return """
    <h1>Audio-to-Text System - Enhanced Features</h1>
    <p>Offline Language Detection & Word Validation Ready</p>
    
    <h2>Test Language Detection:</h2>
    <form action="/detect_language" method="get">
        <input name="text" placeholder="Enter text to detect language" style="width:300px">
        <button type="submit">Detect Language</button>
    </form>
    
    <h2>Test Word Validation:</h2>
    <form action="/validate_word" method="get">
        <input name="word" placeholder="Word to validate">
        <select name="lang">
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="hi">Hindi</option>
        </select>
        <input name="user" placeholder="User ID" value="test_user">
        <button type="submit">Validate Word</button>
    </form>
    
    <h2>View User Words:</h2>
    <a href="/user_words?user=test_user">View All Validated Words</a>
    
    <p><strong>Note:</strong> Install sounddevice and vosk for full audio functionality</p>
    """

@app.route("/validate_word")
def validate_word():
    word = request.args.get("word")
    language = request.args.get("lang", "en")
    user_id = request.args.get("user", "test_user")
    if not word:
        return jsonify({"error": "Word parameter required"})
    result = word_validator.validate_and_store_word(user_id, word, language)
    return jsonify(result)

@app.route("/user_words")
def get_user_words():
    user_id = request.args.get("user", "test_user")
    language = request.args.get("lang")
    words = word_validator.get_user_words(user_id, language)
    return jsonify(words)

@app.route("/detect_language")
def detect_language():
    text = request.args.get("text", "")
    detected = lang_detector.detect_language(text)
    return jsonify({"text": text, "detected_language": detected})

if __name__ == "__main__":
    print("Enhanced Audio-to-Text System")
    print("Features: Offline Language Detection + Word Validation")
    print("Access: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)