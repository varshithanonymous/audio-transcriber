# LinguaVoice Deployment Guide 🚀

This guide provides instructions on how to deploy the LinguaVoice application to a production environment.

## Prerequisites
- **Python 3.9+**
- **pip** (Python package manager)
- **Git**

## 1. Environment Configuration
The application requires a Gemini API key for AI Tutor features.

### Local Config
1. Create/edit `config.py` in the root directory:
```python
GEMINI_API_KEY = "your_gemini_api_key_here"
```

### Production Environment Variables
If deploying to platforms like Render, Railway, or a VPS, set these environment variables:
- `GEMINI_API_KEY`: Your Google Gemini API key.
- `FLASK_SECRET_KEY`: A secure random string for session signing.

## 2. Dependency Installation
Install the required Python packages:
```bash
pip install -r requirements.txt
```

> [!IMPORTANT]
> **Vosk Models**: The application requires Vosk models for offline transcription. Ensure the `vosk-model-small-*` directories are present in the project root.

## 3. Database Initialization
The application uses SQLite. Databases are automatically initialized on startup, but you can run migrations if needed:
```bash
python migrate_db.py
```

## 4. Running the Application

### Development
```bash
python app.py
```

### Production (Recommended)
Use a WSGI server like **Gunicorn**:
```bash
pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```

## 5. Deployment Options

### VPS (AWS/DigitalOcean/Linode)
1. Clone the repository.
2. Install Python and dependencies.
3. Configure a systemd service to run the Gunicorn process.
4. Use **Nginx** as a reverse proxy to handle SSL and port 80/443 mapping.

### Containerization (Docker)
Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["gunicorn", "--bind", ":5000", "app:app"]
```

## Troubleshooting
- **Mic Access**: Browsers require HTTPS for microphone access. Ensure your production site uses SSL.
- **Model Size**: If deploying to a memory-constrained server, ensure the Vosk models fit in RAM.
- **Timeout**: Speech processing can take time; set a sufficient timeout in your WSGI configuration.
