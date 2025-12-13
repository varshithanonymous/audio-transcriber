#!/usr/bin/env python3
"""Test script to verify Vosk models are properly loaded"""

import os
import sys

try:
    import vosk
except ImportError:
    print("ERROR: vosk module not installed. Install with: pip install vosk")
    sys.exit(1)

# Model paths
MODEL_PATHS = {
    "en": "models/en",
    "es": "models/es",
    "hi": "models/hi"
}

def check_model_files(lang, path):
    """Check if required model files exist"""
    required_files = [
        "am/final.mdl",
        "conf/model.conf",
        "graph/HCLr.fst",
        "graph/Gr.fst"
    ]
    
    missing = []
    for file in required_files:
        full_path = os.path.join(path, file)
        if not os.path.exists(full_path):
            missing.append(file)
    
    return missing

def test_model_loading():
    """Test loading all models"""
    print("=" * 60)
    print("Testing Vosk Model Loading")
    print("=" * 60)
    
    all_ok = True
    
    for lang, path in MODEL_PATHS.items():
        print(f"\n[{lang.upper()}] Testing model at: {path}")
        
        # Check if path exists
        if not os.path.exists(path):
            print(f"  ❌ ERROR: Model directory not found: {path}")
            all_ok = False
            continue
        
        # Check required files
        missing = check_model_files(lang, path)
        if missing:
            print(f"  ❌ ERROR: Missing required files:")
            for file in missing:
                print(f"      - {file}")
            all_ok = False
            continue
        
        # Try to load the model
        try:
            print(f"  ✓ All required files found")
            print(f"  → Loading model...")
            model = vosk.Model(path)
            recognizer = vosk.KaldiRecognizer(model, 16000)
            print(f"  ✓ SUCCESS: Model loaded successfully!")
            print(f"     Model sample rate: 16000 Hz")
        except Exception as e:
            print(f"  ❌ ERROR: Failed to load model: {e}")
            all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ ALL MODELS LOADED SUCCESSFULLY!")
        print("=" * 60)
        return True
    else:
        print("❌ SOME MODELS FAILED TO LOAD")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_model_loading()
    sys.exit(0 if success else 1)

