# Quick Railway Deployment Guide 🛤️

Railway is perfect for LinguaVoice. Follow these 5 simple steps:

## 1. Prepare
Ensure you have the `Dockerfile` in your root (the same one we used for Render).

## 2. Deploy
1. Go to [Railway.app](https://railway.app/).
2. Click **New Project** > **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically detect the `Dockerfile` and start building.

## 3. Environment Variables
Go to the **Variables** tab in your Railway service and add:
- `GEMINI_API_KEY`: Your Google Gemini API Key.
- `FLASK_SECRET_KEY`: A secure random string.
- `PORT`: `5000`

## 4. Persistent Storage (For your Database)
Railway resets your files on every deploy. To save your user data:
1. Go to your project settings in Railway.
2. Click **Add Service** > **Volume**.
3. Mount it to `/app/data`.
4. **Code Change**: Ensure `DB_NAME` in `database_manager.py` points to `data/linguavoice.db`.

## 5. Done!
Railway will provide a public URL. Your app is now live and secured with HTTPS (required for the mic).

---

### Why Railway?
- **Automatic HTTPS**: No setup needed for the mic to work.
- **Docker Support**: Installs all the required audio drivers for Vosk automatically.
- **Easy Logs**: If the transcriber has an issue, you'll see it instantly in the "Logs" tab.
