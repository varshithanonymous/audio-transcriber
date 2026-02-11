import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"
SESSION = requests.Session()

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg):
    print(f"❌ FAIL: {msg}")

def test_homepage_redirect():
    try:
        r = SESSION.get(BASE_URL)
        if r.status_code == 200 and "Landing Page" in r.text or "redirect" in r.url or "login" in r.url:
             print_pass("Homepage load / redirect")
        else:
             print_fail(f"Homepage load. Status: {r.status_code}")
    except Exception as e:
        print_fail(f"Homepage load: {e}")

def test_signup_login():
    # Random email to ensure unique
    email = f"test_{int(time.time())}@example.com"
    password = "password123"
    name = "Test User"
    
    print(f"\n--- Testing Auth with {email} ---")
    
    # Signup
    try:
        r = SESSION.post(f"{BASE_URL}/signup", data={
            "name": name, 
            "email": email, 
            "password": password
        })
        if r.status_code == 200 and "login" in r.url:
            print_pass("Signup successful")
        else:
            print_fail(f"Signup failed. Status: {r.status_code}")
    except Exception as e:
        print_fail(f"Signup error: {e}")
        return False

    # Login
    try:
        r = SESSION.post(f"{BASE_URL}/login", data={
            "email": email, 
            "password": password
        })
        if r.status_code == 200 and "dashboard" in r.url:
            print_pass("Login successful")
            return True
        else:
            print_fail("Login failed")
            return False
    except Exception as e:
        print_fail(f"Login error: {e}")
        return False

def test_dashboard():
    try:
        r = SESSION.get(f"{BASE_URL}/dashboard")
        if r.status_code == 200 and "Test User" in r.text:
            print_pass("Dashboard loaded with user name")
        else:
            print_fail("Dashboard load failed")
    except Exception as e:
        print_fail(f"Dashboard error: {e}")

def test_transcription_endpoints():
    print("\n--- Testing Transcription API ---")
    
    # 1. Save Transcript (New Endpoint)
    try:
        payload = {"text": "Hello world testing", "language": "en"}
        r = SESSION.post(f"{BASE_URL}/api/save_transcript", json=payload)
        if r.status_code == 200 and r.json().get("success"):
            print_pass("Save transcript endpoint")
        else:
            print_fail(f"Save transcript failed: {r.text}")
    except Exception as e:
        print_fail(f"Save transcript error: {e}")

    # 2. Get Live Transcripts (New Endpoint)
    try:
        r = SESSION.get(f"{BASE_URL}/api/get_live_transcripts")
        if r.status_code == 200:
            data = r.json()
            if "transcripts" in data:
                print_pass("Get live transcripts endpoint")
                # Check if our saved text appears (might need a second sleep for db commit)
                found = any("Hello world testing" in t['text'] for t in data['transcripts'])
                if found:
                    print_pass("Saved transcript found in live feed")
                else:
                    print_fail("Saved transcript NOT found in live feed (could be timing)")
            else:
                print_fail("Invalid response format for live transcripts")
        else:
            print_fail(f"Get live transcripts failed: {r.status_code}")
    except Exception as e:
        print_fail(f"Get live transcripts error: {e}")

def test_ai_features():
    print("\n--- Testing AI Features ---")
    # 1. AI Tutor Chat
    try:
        payload = {
            "message": "Hola",
            "base_language": "en",
            "target_language": "es",
            "history": []
        }
        r = SESSION.post(f"{BASE_URL}/api/ai_tutor_chat", json=payload)
        if r.status_code == 200:
            data = r.json()
            if "reply" in data and data["reply"]:
                print_pass("AI Tutor Chat response received")
            else:
                print_fail("AI Tutor Chat empty response")
        else:
            print_fail(f"AI Tutor Chat failed: {r.status_code}")
    except Exception as e:
        print_fail(f"AI Tutor Chat error: {e}")

    # 2. Practice Phrase
    try:
        payload = {"base_language": "en", "target_language": "es"}
        r = SESSION.post(f"{BASE_URL}/api/ai_voice_phrase", json=payload)
        if r.status_code == 200:
            data = r.json()
            if "phrase" in data:
                print_pass("AI Practice Phrase received")
            else:
                print_fail("AI Practice Phrase format error")
        else:
             print_fail(f"AI Practice Phrase failed: {r.status_code}")
    except Exception as e:
        print_fail(f"AI Practice Phrase error: {e}")

if __name__ == "__main__":
    print("Wait for server to start manually or ensure it's running on port 5000...")
    # Wait a bit just in case user just restarted
    time.sleep(2)
    
    test_homepage_redirect()
    if test_signup_login():
        test_dashboard()
        test_transcription_endpoints()
        test_ai_features()
    else:
        print("Skipping authenticated tests due to login failure")
