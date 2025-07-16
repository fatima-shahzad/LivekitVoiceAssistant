import os
import asyncio
import time
import queue
import sounddevice as sd
from livekit import api
import numpy as np
import wave
import speech_recognition as sr
import google.generativeai as genai
from gtts import gTTS
from playsound import playsound
from livekit import rtc
from dotenv import load_dotenv
import audioop

# Load environment
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_TOKEN = os.getenv("LIVEKIT_TOKEN")
model = genai.GenerativeModel("gemini-1.5-flash")

# Audio parameters
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
ENERGY_THRESHOLD = 200
SILENCE_DURATION = 1.5  # ⏱️ More forgiving silence

# Records audio until speech ends naturally
def dynamic_record(filename="input.wav"):
    print("🎙️ Listening... Say something (say 'exit' to exit)")
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(bytes(indata))

    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK,
        dtype='int16',
        channels=CHANNELS,
        callback=callback
    )

    audio_frames = []
    silence_start = None
    start_time = time.time()

    # 🔁 NEW: store silent tail buffer (0.5 sec)
    tail_buffer = []
    tail_buffer_frames = int(SAMPLE_RATE * 0.5 / CHUNK)  # number of chunks in 0.5 sec

    with stream:
        while True:
            frame = q.get()
            rms = audioop.rms(frame, 2)

            if rms > ENERGY_THRESHOLD:
                silence_start = None
                audio_frames.extend(tail_buffer)  # flush tail buffer
                tail_buffer.clear()
                audio_frames.append(frame)
            else:
                if audio_frames:
                    tail_buffer.append(frame)
                    if len(tail_buffer) > tail_buffer_frames:
                        tail_buffer.pop(0)

                    if silence_start is None:
                        silence_start = time.time()
                    elapsed_speech = time.time() - start_time
                    if elapsed_speech > 1.0 and time.time() - silence_start > SILENCE_DURATION:
                        audio_frames.extend(tail_buffer)  # include last bit of silence
                        break

    if not audio_frames:
        print("🛑 No valid speech detected.")
        return None

    audio_data = b''.join(audio_frames)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data)

    print("✅ Finished recording.")
    return filename

# Transcribes speech to text
def transcribe_audio(path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text.lower().strip()
        except Exception as e:
            print("❌ Could not understand. Error:", str(e))
            return None

# Sends to Gemini
def ask_gemini(prompt):
    response = model.generate_content(prompt)
    return response.text.strip()

# Speaks response
def speak_response(text):
    filename = f"response_{int(time.time())}.mp3"
    print(f"🤖 Gemini: {text}")
    tts = gTTS(text, lang='en')
    tts.save(filename)
    playsound(filename)
    os.remove(filename)

# Connect to LiveKit
async def connect_livekit():
    # Generate fresh token
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    ).with_identity("fatima")\
     .with_grants(api.VideoGrants(room_join=True, room="my-room"))

    jwt_token = token.to_jwt()

    # ✅ Print the token to use in frontend
    print("\n🔑 LiveKit JWT Token:")
    print(jwt_token)
    # print("🌐 You can use this in the browser:\n"
        #   f"https://firstproject-d8yd3sey.livekit.cloud?token={jwt_token}\n")

    room = rtc.Room()
    await room.connect(os.getenv("LIVEKIT_URL"), jwt_token)
    print(f"✅ Connected to LiveKit room: {room.name}")
    return room

# Main assistant loop
async def main():
    await connect_livekit()
    print("🤖 Gemini is ready. Speak freely. Say 'stop' to end.")

    while True:
        file = dynamic_record()
        if not file:
            continue

        user_input = transcribe_audio(file)
        if not user_input:
            continue

        print(f"🗣️ You said: {user_input}")

        # Only stop if user said exactly 'stop', 'exit', or 'quit'
        if user_input.strip() in ["stop", "exit", "quit"]:
            print("🛑 Voice command detected: stopping.")
            break

        reply = ask_gemini(user_input)
        speak_response(reply)

# Entry
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopped manually.")
