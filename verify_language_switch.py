import requests
import time

BASE_URL = "http://127.0.0.1:5000"
SESSION = requests.Session()

def test_language_switch():
    print("--- Testing Language Switch API ---")
    
    # Login first
    email = "test@example.com" # Use an existing user if possible or signup
    password = "password123"
    
    # Attempt login
    r = SESSION.post(f"{BASE_URL}/login", data={"email": email, "password": password})
    if r.status_code != 200:
        # Try signup if login fails
        email = f"test_lang_{int(time.time())}@example.com"
        r = SESSION.post(f"{BASE_URL}/signup", data={"name": "Test", "email": email, "password": password})
        SESSION.post(f"{BASE_URL}/login", data={"email": email, "password": password})

    languages = ['es', 'hi', 'en']
    
    for lang in languages:
        try:
            r = SESSION.post(f"{BASE_URL}/api/set_language", json={"language": lang})
            if r.status_code == 200 and r.json().get("language") == lang:
                print(f"✅ PASS: Switched to {lang}")
            else:
                print(f"❌ FAIL: Switch to {lang} failed. Status: {r.status_code}, Resp: {r.text}")
        except Exception as e:
            print(f"❌ FAIL: Error switching to {lang}: {e}")

if __name__ == "__main__":
    test_language_switch()
