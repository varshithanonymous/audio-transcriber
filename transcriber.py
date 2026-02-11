import os, queue, json, time, threading, wave
try:
    import sounddevice as sd
except ImportError:
    print("Warning: sounddevice not available, audio recording disabled")
    sd = None
import vosk
from database_manager import db # Unified DB

from language_detector import OfflineLanguageDetector

# Global Active User Context
active_user_id = None

# Initialize Detector
lang_detector = OfflineLanguageDetector()

def set_active_user(user_id):
    global active_user_id
    active_user_id = user_id
    print(f"[TRANSCRIBER] Active user set to: {user_id}", flush=True)

# Global Active Language (Default: English)
active_language = "en"

def set_active_language(lang):
    global active_language
    if lang in MODEL_PATHS:
        active_language = lang
        print(f"[TRANSCRIBER] Active language set to: {lang}", flush=True)
    else:
        print(f"[TRANSCRIBER] Warning: Invalid language '{lang}' requested", flush=True)

    
def detect_language_offline(text):
    return lang_detector.detect_language(text)



# Paths to models
MODEL_PATHS = {
    "en": "models/en",
    "es": "models/es",
    "hi": "models/hi"
}

models = {}
recognizers = {}
print("Loading Vosk models...", flush=True)
for lang, path in MODEL_PATHS.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model directory not found for {lang}: {path}\nDownload model from: https://alphacephei.com/vosk/models")
    try:
        print(f"  Loading {lang.upper()} model from {path}...", flush=True)
        m = vosk.Model(path)
        models[lang] = m
        rec = vosk.KaldiRecognizer(m, 16000)
        rec.SetWords(True) # Enable word timestamps and confidence
        recognizers[lang] = rec
        print(f"  [OK] {lang.upper()} model loaded successfully", flush=True)
    except Exception as e:
        raise RuntimeError(f"Failed to load {lang} model from {path}: {e}\nMake sure the model files are properly extracted.")
print(f"[OK] All {len(recognizers)} models loaded successfully!", flush=True)

DB_FILE = "transcriptions.db"
AUDIO_DIR = "audio_clips"
os.makedirs(AUDIO_DIR, exist_ok=True)

q = queue.Queue()
stop_event = threading.Event()
listener_thread = None


from adaptive_chatbot import AdaptiveChatbot

# Initialize Chatbot for Learning Tracking
chatbot = AdaptiveChatbot()

def validate_word_task(user_id, word, lang):
    # This is a helper to bridge the gap since we are refactoring
    # Ideally, WordValidator should be singleton or util
    from word_validator import WordValidator
    validator = WordValidator()
    validator.validate_and_store_word(user_id, word, lang)


# Replaces init_db and standardizes saving
def save_transcript(text, lang, audio_path=None):
    if active_user_id is None:
        # print("No active user, skipping transcript save", flush=True)
        return

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO transcripts (user_id, timestamp, language, text, audio_file) VALUES (?, ?, ?, ?, ?)",
        (active_user_id, ts, lang, text, audio_path)
    )
    conn.commit()
    conn.close()
    
    # 2. Process Spoken Words (The "Working" Logic for Tracking & Stats)
    # This updates frequencies, user progress, and identifies new words
    try:
        processed_stats = chatbot.process_spoken_words(active_user_id, text, lang)
        
        # 3. Trigger Validation for NEW words (found by chatbot)
        # We only need to validate words that are genuinely new/OOV to save resources
        if processed_stats and 'new_words' in processed_stats:
            for new_word in processed_stats['new_words']:
                threading.Thread(target=validate_word_task, args=(active_user_id, new_word, lang), daemon=True).start()
                
    except Exception as e:
        print(f"Error processing spoken words: {e}", flush=True)


def save_audio_chunk(raw_data, lang):
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{lang}_{ts}.wav"
    filepath = os.path.join(AUDIO_DIR, filename)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(raw_data)
    return filepath

def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status, flush=True)
    q.put(bytes(indata))

def has_speech_activity(audio_data, threshold=500):
    """
    Detect if audio chunk contains actual speech based on energy levels.
    Returns True if speech is likely present.
    """
    import struct
    
    # Convert bytes to samples
    samples = struct.unpack(f'{len(audio_data)//2}h', audio_data)
    
    # Calculate RMS (Root Mean Square) energy
    sum_squares = sum(s * s for s in samples)
    rms = (sum_squares / len(samples)) ** 0.5
    
    # Check if energy exceeds threshold (Lowered to 100)
    return rms > 100

def calculate_audio_quality(audio_data):
    """
    Calculate a quality score for the audio chunk.
    Returns a value between 0 and 1.
    """
    import struct
    
    samples = struct.unpack(f'{len(audio_data)//2}h', audio_data)
    
    # Calculate signal strength
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    
    # Calculate zero-crossing rate (helps detect speech vs noise)
    zero_crossings = sum(1 for i in range(1, len(samples)) 
                        if samples[i] * samples[i-1] < 0)
    zcr = zero_crossings / len(samples)
    
    # Normalize and combine metrics
    # Good speech typically has RMS > 500 and ZCR between 0.05-0.2
    rms_score = min(rms / 2000, 1.0)
    zcr_score = 1.0 if 0.05 <= zcr <= 0.25 else 0.5
    
    return (rms_score + zcr_score) / 2

def transcribe_loop():
    global is_listening
    if sd is None:
        print("Audio recording not available")
        is_listening = False
        return

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000,
                               dtype="int16", channels=1,
                               callback=audio_callback):
            print("[MIC] Listening... (EN, ES, HI + offline detection + validation)")
            is_listening = True
            
            # Continuous recording buffer
            audio_buffer = bytearray()
            CHUNK_DURATION_SEC = 3
            BYTES_PER_SEC = 16000 * 2 # 16kHz * 16-bit
            CHUNK_SIZE = BYTES_PER_SEC * CHUNK_DURATION_SEC
            last_saved_audio_path = None

            while not stop_event.is_set():
                data = q.get()
                if stop_event.is_set():
                    break
                if not data:
                    continue
                
                # 1. Accumulate audio data
                audio_buffer.extend(data)
                
                # 2. Save only high-quality audio chunks every 3 seconds
                if len(audio_buffer) >= CHUNK_SIZE:
                    chunk_to_save = audio_buffer[:CHUNK_SIZE]
                    audio_buffer = audio_buffer[CHUNK_SIZE:] # Keep remainder for next chunk
                    
                    # ===== DEBUG: Check audio levels =====
                    import struct
                    samples = struct.unpack(f'{len(chunk_to_save)//2}h', chunk_to_save)
                    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
                    
                    print(f"[DEBUG] Audio RMS Energy: {rms:.1f} (threshold: 200)", flush=True)
                    
                    # Lower threshold for better sensitivity
                    if has_speech_activity(chunk_to_save, threshold=100):
                        audio_quality = calculate_audio_quality(chunk_to_save)
                        
                        # Save with very low threshold for testing
                        if audio_quality > 0.01:
                            ts_check = time.time()
                            last_saved_audio_path = save_audio_chunk(chunk_to_save, "rec")
                            print(f"[SYSTEM] ✓ Audio Saved: {last_saved_audio_path} (RMS: {rms:.1f}, Quality: {audio_quality:.2f})", flush=True)
                        else:
                            print(f"[SYSTEM] Audio quality too low ({audio_quality:.2f}), skipping save", flush=True)
                            last_saved_audio_path = None
                    else:
                        print(f"[SYSTEM] No speech detected (RMS: {rms:.1f} < threshold 50), skipping save", flush=True)
                        last_saved_audio_path = None

                # 3. Process transcription with improved logic
                # Only run the recognizer for the active language to prevent cross-talk and confusion
                
                target_lang = active_language
                if target_lang in recognizers:
                    rec = recognizers[target_lang]
                    
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip()
                        lang = target_lang # Explicitly set valid language
                        
                        # ===== FILTER 1: Skip empty or very short text =====
                        
                        # ===== FILTER 1: Skip empty or very short text =====
                        if not text or len(text) < 3:
                            continue
                        
                        # Calculate confidence from word-level results
                        confidence = 0
                        word_count = 0
                        if "result" in result and result["result"]:
                            word_results = result["result"]
                            conf_sum = sum(w.get("conf", 0.0) for w in word_results)
                            word_count = len(word_results)
                            confidence = conf_sum / word_count if word_count > 0 else 0
                        
                        # ===== FILTER 2: Minimum confidence threshold (Lowered) =====
                        if confidence < 0.1:
                            print(f"[FILTER] Low confidence ({confidence:.2f}) for '{text}', skipping", flush=True)
                            continue
                        
                        # ===== FILTER 3: Minimum word count for non-Hindi =====
                        # Very short transcriptions may be noise, but allow single words with good confidence
                        if lang in ['en', 'es'] and word_count < 1:
                            print(f"[FILTER] Too few words ({word_count}) for '{text}', skipping", flush=True)
                            continue
                        
                        # Language-specific validation with stricter rules
                        is_valid = False
                        detected_lang = lang  # Default to the model's language
                        
                        # Hindi: Check for Devanagari script
                        if lang == 'hi':
                            devanagari_chars = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
                            total_chars = len(text)
                            
                            # At least 70% of characters should be Devanagari for Hindi
                            if devanagari_chars > 0 and (devanagari_chars / total_chars) >= 0.7:
                                is_valid = True
                                detected_lang = 'hi'
                                print(f"[HI] ✓ Clean Hindi: {text} (conf: {confidence:.2f}, words: {word_count})", flush=True)
                            else:
                                print(f"[FILTER] Insufficient Devanagari content ({devanagari_chars}/{total_chars}), skipping", flush=True)
                        
                        # Spanish: Check for Spanish-specific patterns
                        elif lang == 'es':
                            # Check for Spanish-specific characters
                            has_spanish_chars = any(c in text for c in 'áéíóúüñÁÉÍÓÚÜÑ¿¡')
                            # Use offline detector
                            offline_detected = detect_language_offline(text)
                            
                            # More strict: require either Spanish chars OR confident offline detection
                            if has_spanish_chars or offline_detected == 'es':
                                # Double-check it's not actually English
                                if offline_detected != 'en':
                                    is_valid = True
                                    detected_lang = 'es'
                                    print(f"[ES] ✓ Clean Spanish: {text} (conf: {confidence:.2f}, words: {word_count})", flush=True)
                                else:
                                    print(f"[FILTER] Detected as English, skipping from ES model", flush=True)
                            else:
                                print(f"[FILTER] No Spanish indicators found, skipping", flush=True)
                        
                        # English: Default, but verify it's not another language
                        elif lang == 'en':
                            # Check it's not Hindi (no Devanagari)
                            has_devanagari = any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in text)
                            if has_devanagari:
                                print(f"[FILTER] Contains Devanagari in EN model, skipping", flush=True)
                                continue
                            
                            # Check for Spanish contamination
                            spanish_char_count = sum(1 for c in text if c in 'áéíóúüñÁÉÍÓÚÜÑ¿¡')
                            if spanish_char_count / len(text) > 0.3:
                                print(f"[FILTER] Too many Spanish chars in EN model, skipping", flush=True)
                                continue
                            
                            # Use offline detector for final validation
                            offline_detected = detect_language_offline(text)
                            if offline_detected in ['en', 'unknown']:
                                is_valid = True
                                detected_lang = 'en'
                                print(f"[EN] ✓ Clean English: {text} (conf: {confidence:.2f}, words: {word_count})", flush=True)
                            else:
                                print(f"[FILTER] Detected as {offline_detected}, skipping from EN model", flush=True)
                        
                        # ===== SAVE ONLY VALID, HIGH-QUALITY TRANSCRIPTIONS =====
                        # Must pass all filters
                        if is_valid:
                            # Prefer saving with audio, but save text regardless
                            final_audio_path = last_saved_audio_path if last_saved_audio_path else None
                            
                            if final_audio_path:
                                print(f"[✓ SAVED] [{detected_lang.upper()}] {text} → {final_audio_path}", flush=True)
                            else:
                                print(f"[✓ SAVED] [{detected_lang.upper()}] {text} (No Audio)", flush=True)
                                
                            save_transcript(text, detected_lang, final_audio_path)
    except Exception as e:
        print(f"Audio error: {e}")
    finally:
        is_listening = False

def start_transcriber():
    global listener_thread
    if listener_thread and listener_thread.is_alive():
        return
    stop_event.clear()
    listener_thread = threading.Thread(target=transcribe_loop, daemon=True)
    listener_thread.start()

def stop_transcriber():
    stop_event.set()
    q.put(b"")  # unblock queue
