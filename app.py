from flask import Flask, render_template, jsonify, request, redirect, session, url_for, flash
import os
import transcriber
import threading
import sqlite3
import random
from database_manager import db
from adaptive_chatbot import AdaptiveChatbot
from word_validator import WordValidator
from language_detector import OfflineLanguageDetector
from conversation_engine import conversation_engine
from api_service import api_service

# Initialize Gemini Service
try:
    from config import GEMINI_API_KEY
    from gemini_service import GeminiWordService, gemini_service as gs
    import gemini_service
    gemini_service.gemini_service = GeminiWordService(GEMINI_API_KEY)
    print("[APP] Gemini API initialized successfully")
except Exception as e:
    print(f"[APP] Warning: Could not initialize Gemini API: {e}")
    print("[APP] Word meanings will use fallback dictionary APIs")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_linguavoice_2024_dev_only")
chatbot = AdaptiveChatbot()
word_validator = WordValidator()
lang_detector = OfflineLanguageDetector()
transcriber.start_transcriber()

def get_current_user_id():
    return session.get("user_id")

def is_logged_in():
    return "user_id" in session

# --- Routes: Auth ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.login_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            transcriber.set_active_user(user["id"]) # Connect audio to this user
            return redirect("/dashboard")
        else:
            flash("Invalid email or password", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        if db.register_user(email, password, name):
            flash("Account created! Please log in.", "success")
            return redirect("/login")
        else:
            flash("Email already registered.", "error")
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    transcriber.set_active_user(None)
    return redirect("/login")

# --- Routes: Main App ---
@app.route("/")
def index():
    if is_logged_in():
        return redirect("/dashboard")
    return redirect("/landing")

@app.route("/landing")
def landing():
    return render_template("landing.html")

@app.route("/dashboard")
def dashboard():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("dashboard_modern.html", user_name=user_name)

@app.route("/transcription")
def transcription_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("transcription_modern.html", user_name=user_name)

@app.route("/tutor")
def tutor_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    # Get target language
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'es'
    
    # Get current level to fetch appropriate content
    cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
    completed = [r[0] for r in cursor.fetchall()]
    current_level = max(completed) + 1 if completed else 1
    conn.close()
    
    return render_template("tutor.html", user_name=user_name, target_language=target_language, current_level=current_level)

@app.route("/api/tutor/get_content")
def get_tutor_content():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    
    user_id = get_current_user_id()
    level_id = int(request.args.get('level', 1))
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'es'
    conn.close()
    
    from level_generator import level_generator
    words = level_generator.generate_level_content(level_id, target_language)
    
    # Store in session for quiz consistency if they switch to quiz mode in tutor
    session[f'level_{level_id}_words'] = words
    
    return jsonify({"words": words, "level": level_id})

@app.route("/vocabulary")
def vocabulary_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("vocabulary_modern.html", user_name=user_name)
@app.route("/learning_path")
def learning_path_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    # Fetch progress from DB
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Table creation moved to database_manager.py

    
    # Fetch completed levels
    cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
    completed_levels = [row[0] for row in cursor.fetchall()]
    
    # Fetch target language
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row else None
    
    # If not set, check if we can infer from user_progress (legacy)
    if not target_language:
        cursor.execute("SELECT language FROM user_progress WHERE user_id=? ORDER BY last_activity DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        if row:
             target_language = row[0]
             # Backfill
             cursor.execute("UPDATE users SET target_language=? WHERE id=?", (target_language, user_id))
             conn.commit()

    conn.close()
    
    # Determine current level (max completed + 1)
    current_level = max(completed_levels) + 1 if completed_levels else 1
    
    return render_template("learning_path.html", user_name=user_name, completed_levels=completed_levels, current_level=current_level, target_language=target_language)

@app.route("/api/set_target_language", methods=["POST"])
def set_target_language():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    lang = data.get("language")
    
    if not lang:
        return jsonify({"error": "No language provided"}), 400
        
    user_id = get_current_user_id()
    conn = db.get_connection()
    try:
        conn.execute("UPDATE users SET target_language=? WHERE id=?", (lang, user_id))
        conn.commit()
    except Exception as e:
        print(f"[API] Error setting language: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
        
    return jsonify({"success": True})

@app.route("/learning/level/<int:level_id>/flashcards")
def level_flashcards(level_id):
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    # Get user's target language
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'es' # Default to Spanish
    conn.close()
    
    # Generate words for this level
    from level_generator import level_generator
    words = level_generator.generate_level_content(level_id, target_language)
    
    # Store words in session for quiz consistency
    session[f'level_{level_id}_words'] = words
    
    print(f"[DEBUG] Level {level_id} words ({target_language}): {words}")
    
    return render_template("flashcards.html", user_name=user_name, level_id=level_id, words=words)
@app.route("/learning/level/<int:level_id>/quiz")
def level_quiz(level_id):
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("quiz.html", user_name=user_name, level_id=level_id)

@app.route("/learning")
def learning_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("learning_modern.html", user_name=user_name)

@app.route("/analytics")
def analytics_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("analytics_modern.html", user_name=user_name)


@app.route("/notes")
@app.route("/public/notes")
def notes_page():
    # If explicitly public or not logged in, show as guest
    is_public = request.path.startswith('/public')
    user_id = get_current_user_id() if is_logged_in() else None
    
    target_language = 'es'
    if user_id:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        target_language = row[0] if row and row[0] else 'es'
        conn.close()
    
    return render_template("notes.html", target_language=target_language, is_public=is_public)

@app.route("/api/notes/translate", methods=["POST"])
def api_translate_note():
    # Allow public access for translation
    data = request.json
    text = data.get("text")
    lang = data.get("lang", "es")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    from ai_tutor_service import get_note_translation
    result = get_note_translation(text, lang)
    return jsonify(result)

@app.route("/test")
@app.route("/public/test")
def test_page():
    is_public = request.path.startswith('/public')
    user_name = session.get("user_name", "Guest") if is_logged_in() else "Explorer"
    user_id = get_current_user_id() if is_logged_in() else None
    
    target_language = 'es'
    current_level = 1
    
    if user_id:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        target_language = row[0] if row and row[0] else 'es'
        
        cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
        completed = [r[0] for r in cursor.fetchall()]
        current_level = max(completed) + 1 if completed else 1
        conn.close()
    
    return render_template("test.html", user_name=user_name, target_language=target_language, current_level=current_level, is_public=is_public)

@app.route("/api/public/tutor/get_content")
def api_public_tutor_content():
    """Public version of tutor content for guests"""
    level = request.args.get('level', 1, type=int)
    from level_generator import generate_level_content
    content = generate_level_content(level, 'es') # Default to Spanish for guests
    return jsonify(content)

@app.route("/word_validation")
def word_validation_page():
    if not is_logged_in(): return redirect("/login")
    return render_template("word_validation_enhanced.html")

@app.route("/ai_tutor")
def ai_tutor_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("ai_tutor_modern.html", user_name=user_name)

@app.route("/certificate")
def certificate_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("certificate.html", user_name=user_name, language_name="Spanish", total_xp=5200)

@app.route("/api/save_level_progress", methods=["POST"])
def save_level_progress():
    """Save user's level completion progress"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    level_id = data.get('level_id')
    score = data.get('score')
    xp_earned = data.get('xp_earned')
    passed = data.get('passed')
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Insert or replace execution
        cursor.execute("""
            INSERT OR REPLACE INTO user_completed_levels (user_id, level_id, xp_earned, score, passed)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, level_id, xp_earned, score, passed))
        
        conn.commit()
        conn.close()
        
        if level_id == 100 and passed:
            return jsonify({"success": True, "certificate": True, "redirect": "/certificate"})
        
        return jsonify({"success": True, "next_level": level_id + 1 if passed else level_id})
        
    except Exception as e:
        print(f"[API] Save progress error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@app.route("/validation")
def validation_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("validation_modern.html", user_name=user_name)
@app.route("/update_meanings")
def update_meanings_page():
    if not is_logged_in(): return redirect("/login")
    return render_template("update_meanings.html")

@app.route("/community")
def community_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("community.html", user_name=user_name)


# --- Routes: API ---
@app.route("/api/update_all_meanings")
def update_all_meanings():
    """Fetch meanings for all words using Gemini API"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        conn = sqlite3.connect('lingua_voice.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT word, language, meaning 
            FROM vocabulary 
            WHERE user_name = ?
        """, (session.get('user_name'),))
        
        words = cursor.fetchall()
        updated_count = 0
        
        for word, language, current_meaning in words:
            # Skip if already has good meaning
            if current_meaning and len(current_meaning) > 20 and 'pending' not in current_meaning.lower() and 'uplabdh' not in current_meaning:
                continue
            
            print(f"[API] Fetching: {word} ({language})")
            new_meaning = word_validator.get_word_meaning(word, language)
            
            if new_meaning:
                cursor.execute("""
                    UPDATE vocabulary 
                    SET meaning = ? 
                    WHERE user_name = ? AND word = ? AND language = ?
                """, (new_meaning, session.get('user_name'), word, language))
                updated_count += 1
                print(f"[API] ✓ {word}: {new_meaning[:50]}...")
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "updated": updated_count, "total": len(words)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_transcripts")

def get_transcripts():
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, language, text, audio_file FROM transcripts WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,))
    data = [{"timestamp": r[0], "language": r[1], "text": r[2], "audio_file": r[3]} for r in cursor.fetchall()]
    conn.close()
    return jsonify(data)

@app.route("/api/start_recording", methods=["POST"])
def start_recording():
    """Initialize recording session for the user"""
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    # Ensure transcriber knows who is recording
    transcriber.set_active_user(user_id)
    
    # Also default the language if provided in body, else keep current
    data = request.get_json()
    if data and 'language' in data:
        lang = data.get('language')
        if lang in ['en', 'es', 'hi']:
            transcriber.set_active_language(lang)
            
    return jsonify({"success": True})

@app.route("/api/set_language", methods=["POST"])
def set_language():
    """Set the active transcription language"""
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    lang = data.get('language')
    
    if lang not in ['en', 'es', 'hi']:
        return jsonify({"error": "Invalid language"}), 400
        
    transcriber.set_active_language(lang)
    transcriber.set_active_user(user_id) # Ensure user is also refreshed
    return jsonify({"success": True, "language": lang})

@app.route("/api/save_transcript", methods=["POST"])
def save_manual_transcript():
    """Manually save a transcript from frontend"""
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        text = data.get('text')
        language = data.get('language')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # Use existing logic
        transcriber.set_active_user(user_id)
        transcriber.save_transcript(text, language, audio_path="manual_entry")
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"[API] Error saving transcript: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_live_transcripts")
def get_live_transcripts():
    """Get transcripts from the last 5 seconds for live display"""
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # Fetch transcripts from the last 10 seconds (allow some buffer)
        cursor.execute("""
            SELECT text, language, timestamp 
            FROM transcripts 
            WHERE user_id=? AND timestamp >= datetime('now', '-10 seconds', 'localtime')
            ORDER BY timestamp ASC
        """, (user_id,))
        
        data = [{"text": r[0], "language": r[1], "id": str(r[2])} for r in cursor.fetchall()]
        conn.close()
        return jsonify({"transcripts": data})
    except Exception as e:
        print(f"[API] Error fetching live transcripts: {e}")
        return jsonify({"transcripts": []})

@app.route("/api/stats")
def get_stats():
    user_id = get_current_user_id()
    if not user_id: return jsonify({})
    stats = chatbot.get_user_stats(user_id)
    return jsonify({"stats": stats})

@app.route("/api/validate_word_manual")
def validate_manual():
    user_id = get_current_user_id()
    word = request.args.get("word")
    lang = request.args.get("lang", "en")
    if user_id and word:
        res = word_validator.validate_and_store_word(user_id, word, lang)
        return jsonify(res)
    return jsonify({"error": "Missing params"})

@app.route("/api/get_my_spoken_words")
def get_my_spoken_words():
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    words = word_validator.get_user_words(user_id)
    return jsonify(words)

@app.route("/api/get_vocabulary_bank_full")
def get_vocab_bank_full():
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    words = word_validator.get_user_words(user_id)
    return jsonify(words)

@app.route("/api/get_oov_words")
def get_oov_words_route():
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    oov_words = chatbot.get_oov_words(user_id)
    return jsonify(oov_words)
@app.route("/validate_word")
def validate_word_route():
    user_id = get_current_user_id()
    word = request.args.get("word")
    lang = request.args.get("lang", "en")
    
    if not user_id and request.args.get("user") == "default_user":
        res = word_validator.validate_and_store_word(999, word, lang)
        return jsonify(res)
        
    if user_id and word:
        res = word_validator.validate_and_store_word(user_id, word, lang)
        return jsonify(res)
    return jsonify({"error": "Missing params"})

@app.route("/api/auto_generate_vocab")
def auto_gen_vocab():
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    
    import random
    
    # Get language from query parameter, default to English
    lang = request.args.get('lang', 'en')
    
    # Get user's existing vocabulary to avoid duplicates
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM vocabulary WHERE user_id=?", (user_id,))
    existing_words = set(row[0].lower() for row in cursor.fetchall())
    conn.close()
    
    # Load offline vocabulary for the language
    offline_vocab = chatbot.load_offline_vocab(lang)
    if not offline_vocab:
        return jsonify([])
    
    # Collect all words from all levels
    all_words = []
    for level, words in offline_vocab.items():
        all_words.extend(words)
    
    # Filter out words user already has
    available_words = [w for w in all_words if w.lower() not in existing_words]
    
    # If all words are learned, reset and use all words
    if not available_words:
        available_words = all_words
    
    # Generate 1-N new words based on count param
    try:
        count_param = int(request.args.get('count', 1))
    except:
        count_param = 1
        
    num_words = min(count_param, len(available_words))
    selected_words = random.sample(available_words, num_words)
    
    new_suggestions = []
    for word in selected_words:
        # Validate and store the word
        res = word_validator.validate_and_store_word(user_id, word, lang)
        new_suggestions.append({
            "word": word,
            "language": lang,
            "source": "Incremental Learning",
            "meaning": res.get('meaning', 'Learning in progress...')
        })
    
    return jsonify(new_suggestions)

@app.route("/api/ai_tutor_chat", methods=["POST"])
def ai_tutor_chat():
    """AI Tutor chat endpoint"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        message = data.get('message')
        base_language = data.get('base_language')
        target_language = data.get('target_language')
        history = data.get('history', [])
        
        from ai_tutor_service import get_ai_tutor_response
        reply = get_ai_tutor_response(message, base_language, target_language, history)
        
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"[API] AI Tutor error: {e}")
        return jsonify({"error": str(e)}), 500
@app.route("/api/ai_voice_phrase", methods=["POST"])
def ai_voice_phrase():
    """Get a practice phrase from AI"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        base_language = data.get('base_language')
        target_language = data.get('target_language')
        
        from ai_tutor_service import get_practice_phrase
        phrase_data = get_practice_phrase(base_language, target_language)
        
        return jsonify(phrase_data)
    except Exception as e:
        print(f"[API] AI Voice error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai_check_pronunciation", methods=["POST"])
def ai_check_pronunciation():
    """Check user's pronunciation"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        expected = data.get('expected')
        actual = data.get('actual')
        language = data.get('language')
        
        from ai_tutor_service import check_pronunciation
        result = check_pronunciation(expected, actual, language)
        
        return jsonify(result)
    except Exception as e:
        print(f"[API] Pronunciation check error: {e}")
        return jsonify({"error": str(e)}), 500
@app.route("/api/get_level_quiz", methods=["POST"])
def get_level_quiz():
    """Generate quiz questions for a specific level using Gemini"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        level_id = data.get('level_id', 1)
        user_id = get_current_user_id()
        
        # Get target language
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        target_language = row[0] if row and row[0] else 'es'
        conn.close()
        
        from level_generator import level_generator
        from ai_tutor_service import generate_quiz_questions
        
        # Try to get words from session to ensure quiz matches flashcards
        words = session.get(f'level_{level_id}_words')
        
        # Get level metadata
        metadata = level_generator.get_level_metadata(level_id)
        
        # Generate questions using Gemini
        questions = generate_quiz_questions(level_id, metadata['tier'], target_language, words)
        
        return jsonify({"questions": questions})
    except Exception as e:
        print(f"[API] Quiz generation error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== OOV / VALIDATION ====================

@app.route("/api/check_grammar")
def check_grammar():
    """Check grammar using LanguageTool API"""
    from api_service import api_service
    
    text = request.args.get("text", "")
    language = request.args.get("lang", "en")
    
    if not text:
        return jsonify({"error": "No text provided"})
    
    result = api_service.check_grammar(text, language)
    return jsonify(result)

@app.route("/api/get_word_info")
def get_word_info():
    """Get enhanced word information"""
    from api_service import api_service
    
    word = request.args.get("word", "")
    language = request.args.get("lang", "en")
    
    if not word:
        return jsonify({"error": "No word provided"})
    
    info = api_service.get_enhanced_word_info(word, language)
    return jsonify(info)

@app.route("/api/get_similar_words")
def get_similar_words():
    """Get similar words using Datamuse API"""
    from api_service import api_service
    
    word = request.args.get("word", "")
    
    if not word:
        return jsonify({"error": "No word provided"})
    
    similar = api_service.get_similar_words(word, max_results=10)
    return jsonify({"similar_words": similar})

@app.route("/api/chat_response", methods=["POST"])
def chat_response():
    """Get AI response for the Tutor"""
    data = request.json
    user_text = data.get("text", "")
    language = data.get("language", "en")
    
    if not user_text:
        return jsonify({"response": "", "correction": None})
        
    result = conversation_engine.get_response(user_text, language)
    return jsonify(result)

# --- Audio Serving ---
from flask import send_from_directory
@app.route('/audio_clips/<path:filename>')
def serve_audio(filename):
    return send_from_directory('audio_clips', filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
