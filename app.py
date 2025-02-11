import os
from fastapi import FastAPI, HTTPException
from deepgram import Deepgram
import aiohttp
import requests

app = FastAPI()

# Берём API-ключи из переменных окружения
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")  # Если используем кастомный голос

# 1️⃣ Функция для расшифровки аудио (Deepgram)
async def transcribe_audio(audio_url: str):
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=500, detail="Deepgram API key отсутствует!")
    
    deepgram = Deepgram(DEEPGRAM_API_KEY)
    async with aiohttp.ClientSession() as session:
        response = await deepgram.transcription.prerecorded(
            {"url": audio_url},
            {"punctuate": True, "language": "ru"}
        )
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]

@app.post("/transcribe/")
async def transcribe(audio_url: str):
    try:
        transcript = await transcribe_audio(audio_url)
        return {"transcription": transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2️⃣ Функция для генерации речи AI-HR (ElevenLabs)
def generate_speech(text):
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        raise HTTPException(status_code=500, detail="ElevenLabs API key или Voice ID отсутствуют!")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {"stability": 0.75, "similarity_boost": 0.9}
    }
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.content
    else:
        return None

@app.post("/synthesize/")
def synthesize(text: str):
    speech_audio = generate_speech(text)
    if speech_audio:
        return {"audio": speech_audio}
    else:
        raise HTTPException(status_code=500, detail="Ошибка генерации речи")
        @app.get("/")
def home():
    return {"message": "AI-HR API работает!"}

