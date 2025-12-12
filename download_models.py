import os
import urllib.request
import zipfile

models = {
    'en': 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip',
    'es': 'https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip',
    'hi': 'https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip'
}

def download_model(lang, url):
    model_dir = f"models/{lang}"
    zip_file = f"models/{lang}.zip"
    
    if os.path.exists(model_dir):
        print(f"Model for {lang} already exists")
        return
    
    print(f"Downloading {lang} model...")
    urllib.request.urlretrieve(url, zip_file)
    
    print(f"Extracting {lang} model...")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall("models/")
    
    # Rename extracted folder to language code
    extracted_folders = [f for f in os.listdir("models/") if f.startswith("vosk-model") and lang in f]
    if extracted_folders:
        import shutil
        shutil.move(f"models/{extracted_folders[0]}", model_dir)
    
    os.remove(zip_file)
    print(f"Model for {lang} installed successfully")

if __name__ == "__main__":
    for lang, url in models.items():
        download_model(lang, url)