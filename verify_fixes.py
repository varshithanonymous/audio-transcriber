import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

print("Checking imports...")
try:
    import flask
    print("✓ Flask imported")
except ImportError as e:
    print(f"✗ Flask import failed: {e}")

try:
    import google.generativeai as genai
    print(f"✓ google-generativeai imported (version: {genai.__version__})")
except ImportError as e:
    print(f"✗ google-generativeai import failed: {e}")

print("\nChecking App Configuration...")
try:
    from app import app
    print("✓ App imported")
    
    secret_key = app.secret_key
    print(f"  Secret Key: {secret_key}")
    
    if secret_key == "super_secret_key_linguavoice_2024":
        print("✗ Secret key is still the old hardcoded value!")
    elif "dev_only" in str(secret_key):
        print("✓ Secret key is the safe dev default (or env var not set)")
    else:
        print("✓ Secret key is set to a custom value")
        
except Exception as e:
    print(f"✗ App import/config check failed: {e}")

print("\nChecking Gemini Service Code...")
try:
    from gemini_service import GeminiWordService
    print("✓ GeminiWordService class found")
    # We won't instantiate it as it requires an API key and network
except ImportError as e:
    print(f"✗ GeminiWordService import failed: {e}")

print("\nVerification Complete.")
