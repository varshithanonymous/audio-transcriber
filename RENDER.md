# Deploying LinguaVoice to Render 🚀

This guide provides clear, step-by-step instructions for deploying LinguaVoice to Render.

## 1. Prepare Your Repository
1. Ensure `requirements.txt` is up to date.
2. Ensure your `models/` directory (containing `en`, `es`, `hi`) is included in your git repository.
   - *Note: If individual files are >100MB, use Git LFS.*

## 2. Docker Setup (Recommended)
Since LinguaVoice requires specific system libraries (like `libportaudio` for Vosk/sounddevice), using a Dockerfile is the most reliable method.

Create a `Dockerfile` in the root:
```dockerfile
# Use Python 3.9
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy all files
COPY . .

# Expose port
EXPOSE 5000

# Start with Gunicorn
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]
```

## 3. Create Render Web Service
1. Log in to [Render](https://dashboard.render.com).
2. Click **New +** > **Web Service**.
3. Connect your GitHub repository.
4. **Runtime**: Select `Docker`.
5. **Name**: `linguavoice` (or your preferred name).

## 4. Environment Variables
In the **Environment** tab of your Render service, add:
- `GEMINI_API_KEY`: Your Google Gemini API Key.
- `FLASK_SECRET_KEY`: A random secure string (e.g., `your-secret-key-123`).

## 5. Persistence (Critical for SQLite)
Render's disk is ephemeral. To prevent losing user data:
1. Go to the **Disk** tab.
2. Click **Add Disk**.
3. **Name**: `data`.
4. **Mount Path**: `/app/data`.
5. **Size**: 1 GB is plenty.
6. **Code Update**: Change `DB_NAME` in `database_manager.py` to `data/linguavoice.db`.

## 6. Accessing the Site
Render will provide a URL (e.g., `https://linguavoice.onrender.com`).
> [!IMPORTANT]
> **HTTPS**: Render provides SSL automatically. This is required for microphone access in browsers.

## Troubleshooting
- **Memory Limit**: If the server crashes on startup, it might be running out of memory while loading Vosk models. Consider upgrading to a "Starter" instance (2GB RAM) if the Free tier (512MB) is insufficient.
- **Microphone**: If your browser says "Microphone blocked," ensure you are accessing the site via `https://`.
- **Gunicorn Timeout**: If transcription takes too long, set `GUNICORN_CMD_ARGS="--timeout 120"`.
