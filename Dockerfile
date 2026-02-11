# Use Python 3.9
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libasound2-dev \
    gcc \
    python3-dev \
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

# Start with Gunicorn (using dynamic port for Railway/Render)
CMD gunicorn --workers 1 --bind 0.0.0.0:${PORT:-5000} --timeout 120 app:app
