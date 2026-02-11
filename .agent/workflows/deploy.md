---
description: Steps to deploy the LinguaVoice application to a production server.
---

# LinguaVoice Deployment Workflow

Follow these steps to deploy the application.

1. **Environment Setup**
    - Ensure Python 3.9+ is installed.
    - Set `GEMINI_API_KEY` in `config.py` or as an environment variable.
    - Set a strong `FLASK_SECRET_KEY` environment variable.

2. **Install Dependencies**
    - Run `pip install -r requirements.txt`.
    - Install a WSGI server: `pip install gunicorn`.

3. **Verify Vosk Models**
    - Ensure the directories starting with `vosk-model-` are present in the project root.

4. **Initialize Database**
    - The databases are SQLite and will be created on first run. To manually migrate:
    - Run `python migrate_db.py`.

5. **Start Production Server**
    - Run `gunicorn --workers 4 --bind 0.0.0.0:5000 app:app`.

6. **SSL / HTTPS (CRITICAL)**
    - Browsers require HTTPS for microphone access.
    - Configure Nginx or your cloud provider to provide an SSL certificate for the domain.
