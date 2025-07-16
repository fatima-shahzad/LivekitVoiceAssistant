# 🎙️ Voice Assistant with Gemini & LiveKit

This project is a Python-based voice assistant that:
- Records your speech
- Converts it to text
- Sends it to Google's Gemini 1.5 Flash model
- Speaks back the AI-generated response using gTTS
- Connects to a LiveKit video room

## 💡 Features
- Real-time voice interaction
- Natural stopping with silence detection
- Uses Google Gemini API for smart responses
- Audio output via gTTS and playsound
- LiveKit integration with automatic token generation

## 📦 Dependencies
- `sounddevice`
- `numpy`
- `wave`
- `speechrecognition`
- `gtts`
- `playsound`
- `livekit`
- `google-generativeai`
- `python-dotenv`

## Install them with:
```bash
pip install -r requirements.txt
```

## Create a .env file using the .env.example format

## Run the assistant:
```bash
python main.py

Say 'exit' to stop the assistant
