from flask import Flask, render_template, jsonify, Response, send_from_directory, request
import sqlite3
import csv
import io
import os
import transcriber
from adaptive_chatbot import AdaptiveChatbot

# Enhanced features
class OfflineLanguageDetector:
    def __init__(self):
        self.patterns = {
            'en': {'chars': set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'common_words': {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with'}},
            'es': {'chars': set('abcdefghijklmnopqrstuvwxyzáéíóúüñABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), 'common_words': {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se'}},
            'hi': {'chars': set('अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञ'), 'common_words': {'है', 'का', 'की', 'के', 'में', 'से', 'को', 'और', 'यह', 'वह'}}
        }
    def detect_language(self, text):
        if not text.strip(): return 'unknown'
        scores = {'en': 0, 'es': 0, 'hi': 0}
        words = text.lower().split()
        for lang, data in self.patterns.items():
            char_score = sum(1 for char in text if char in data['chars'])
            scores[lang] += char_score / len(text) * 50
            word_score = sum(1 for word in words if word in data['common_words'])
            scores[lang] += word_score / len(words) * 50 if words else 0
        detected = max(scores, key=scores.get)
        return detected if scores[detected] > 10 else 'unknown'

class WordValidator:
    def __init__(self, db_file="word_database.db"):
        self.db_file = db_file
        self.init_db()
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        conn.execute("CREATE TABLE IF NOT EXISTS validated_words (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, word TEXT, language TEXT, meaning TEXT, is_valid INTEGER, timestamp TEXT, UNIQUE(user_id, word, language))")
        conn.commit()
        conn.close()
    def is_online(self):
        try:
            import requests
            requests.get("https://httpbin.org/status/200", timeout=3)
            return True
        except: return False
    def get_word_meaning(self, word, language):
        if not self.is_online(): return None
        try:
            import requests
            if language == 'en':
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        meanings = data[0].get('meanings', [])
                        if meanings: return meanings[0].get('definitions', [{}])[0].get('definition', '')
            return None
        except: return None
    def validate_and_store_word(self, user_id, word, language):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT meaning, is_valid FROM validated_words WHERE user_id=? AND word=? AND language=?", (user_id, word.lower(), language))
        result = cursor.fetchone()
        if result:
            conn.close()
            return {'cached': True, 'meaning': result[0], 'is_valid': bool(result[1])}
        meaning = self.get_word_meaning(word, language)
        is_valid = meaning is not None
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR REPLACE INTO validated_words (user_id, word, language, meaning, is_valid, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (user_id, word.lower(), language, meaning or '', int(is_valid), timestamp))
        conn.commit()
        conn.close()
        return {'cached': False, 'meaning': meaning, 'is_valid': is_valid}
    def get_user_words(self, user_id, language=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        if language:
            cursor.execute("SELECT word, language, meaning, is_valid, timestamp FROM validated_words WHERE user_id=? AND language=? ORDER BY timestamp DESC", (user_id, language))
        else:
            cursor.execute("SELECT word, language, meaning, is_valid, timestamp FROM validated_words WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
        results = cursor.fetchall()
        conn.close()
        return [{'word': r[0], 'language': r[1], 'meaning': r[2], 'is_valid': bool(r[3]), 'timestamp': r[4]} for r in results]

app = Flask(__name__)
word_validator = WordValidator()
lang_detector = OfflineLanguageDetector()
chatbot = AdaptiveChatbot()

# Start background transcriber
transcriber.start_transcriber()

DB_FILE = "transcriptions.db"
AUDIO_DIR = "audio_clips"

def get_transcripts(limit=None, lang=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if lang and lang != "all":
        query = "SELECT timestamp, language, text, audio_file FROM transcripts WHERE language=? ORDER BY id DESC"
        params = (lang,)
    else:
        query = "SELECT timestamp, language, text, audio_file FROM transcripts ORDER BY id DESC"
        params = ()
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [{"timestamp": r[0], "language": r[1], "text": r[2], "audio_file": r[3]} for r in rows]

@app.route("/")
def index():
    return render_template("main_menu.html")

@app.route("/transcription")
def transcription_page():
    return render_template("transcription.html")

@app.route("/tutor")
def tutor_page():
    return render_template("tutor.html")

@app.route("/validation_page")
def validation_page():
    return render_template("validation.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/dataset")
def dataset_page():
    return render_template("dataset.html")

@app.route("/data")
def data():
    lang = request.args.get("lang", "all")
    return jsonify(get_transcripts(limit=20, lang=lang))

# 🔹 Download TXT
@app.route("/download/txt")
def download_txt():
    transcripts = get_transcripts()
    output = io.StringIO()
    for t in transcripts:
        output.write(f"{t['timestamp']} [{t['language']}] - {t['text']}\n")
    return Response(output.getvalue(),
                    mimetype="text/plain",
                    headers={"Content-Disposition": "attachment;filename=transcripts.txt"})

# 🔹 Download CSV
@app.route("/download/csv")
def download_csv():
    transcripts = get_transcripts()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Language", "Transcript", "AudioFile"])
    for t in transcripts:
        writer.writerow([t['timestamp'], t['language'], t['text'], t['audio_file']])
    return Response(output.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=transcripts.csv"})

# 🔹 Serve audio files
@app.route("/audio_clips/<path:filename>")
def download_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route("/validate_word")
def validate_word():
    word = request.args.get("word")
    language = request.args.get("lang", "en")
    user_id = request.args.get("user", "default_user")
    if not word:
        return jsonify({"error": "Word parameter required"})
    result = word_validator.validate_and_store_word(user_id, word, language)
    return jsonify(result)

@app.route("/user_words")
def get_user_words():
    user_id = request.args.get("user", "default_user")
    language = request.args.get("lang")
    words = word_validator.get_user_words(user_id, language)
    return jsonify(words)

@app.route("/detect_language")
def detect_language():
    text = request.args.get("text", "")
    detected = lang_detector.detect_language(text)
    return jsonify({"text": text, "detected_language": detected})


# -------- Adaptive Chatbot + Tutor Endpoints --------
def _user():
    return request.args.get("user", "default_user")


@app.route("/chatbot/vocabulary")
def chatbot_vocabulary():
    user_id = _user()
    language = request.args.get("lang")
    limit = int(request.args.get("limit", 200))
    vocab = chatbot.get_vocabulary(user_id, language, limit=limit)
    return jsonify({"user": user_id, "items": vocab})


@app.route("/chatbot/new_words")
def chatbot_new_words():
    user_id = _user()
    language = request.args.get("lang")
    days = int(request.args.get("days", 7))
    data = chatbot.get_new_words_by_date(user_id, days=days, language=language)
    return jsonify({"user": user_id, "days": days, "by_date": data})


@app.route("/chatbot/oov")
def chatbot_oov():
    user_id = _user()
    language = request.args.get("lang")
    oov = chatbot.get_oov_words(user_id, language)
    return jsonify({"user": user_id, "items": oov})


@app.route("/chatbot/stats")
def chatbot_stats():
    user_id = _user()
    language = request.args.get("lang")
    stats = chatbot.get_user_stats(user_id, language)
    return jsonify({"user": user_id, "stats": stats})


@app.route("/chatbot/lesson")
def chatbot_lesson():
    user_id = _user()
    language = request.args.get("lang", "en")
    lesson = chatbot.get_personalized_lesson(user_id, language)
    return jsonify({"user": user_id, "language": language, "lesson": lesson})


@app.route("/chatbot/daily_challenge")
def chatbot_daily_challenge():
    user_id = _user()
    language = request.args.get("lang", "en")
    challenge = chatbot.get_daily_challenge(user_id, language)
    return jsonify({"user": user_id, "language": language, "challenge": challenge})


@app.route("/chatbot/record_performance", methods=["POST"])
def chatbot_record_performance():
    payload = request.get_json(force=True, silent=True) or {}
    user_id = payload.get("user", "default_user")
    language = payload.get("lang", "en")
    chatbot.record_performance(
        user_id=user_id,
        language=language,
        word=payload.get("word"),
        lesson_type=payload.get("lesson_type", "practice"),
        response_time=float(payload.get("response_time", 0)),
        is_correct=bool(payload.get("is_correct", False)),
        difficulty_level=payload.get("difficulty_level", "beginner"),
    )
    return jsonify({"status": "recorded"})


@app.route("/chatbot/analytics")
def chatbot_analytics():
    """Aggregate stats for dashboard charts."""
    user_id = request.args.get("user", "default_user")
    stats = chatbot.get_user_stats(user_id)

    # XP per language
    xp_by_lang = {}
    for lang, s in stats.items():
        xp_by_lang[lang] = s.get("total_xp") or s.get("xp") or 0

    # New words count by date (last 7 days)
    new_words_raw = chatbot.get_new_words_by_date(user_id, days=7)
    new_words_by_day = {day: len(words) for day, words in new_words_raw.items()}

    # OOV counts per language
    oov_items = chatbot.get_oov_words(user_id)
    oov_by_lang = {}
    for item in oov_items:
        oov_by_lang[item["language"]] = oov_by_lang.get(item["language"], 0) + item.get("occurrences", 1)

    return jsonify({
        "xp_by_lang": xp_by_lang,
        "new_words_by_day": new_words_by_day,
        "oov_by_lang": oov_by_lang
    })


@app.route("/record/start", methods=["POST"])
def record_start():
    transcriber.stop_event.clear()
    transcriber.start_transcriber()
    return jsonify({"recording": True})


@app.route("/record/stop", methods=["POST"])
def record_stop():
    transcriber.stop_transcriber()
    return jsonify({"recording": False})


@app.route("/record/status")
def record_status():
    running = transcriber.listener_thread is not None and transcriber.listener_thread.is_alive()
    return jsonify({"recording": running})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
