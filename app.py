import os
import smtplib
import uuid
from email.mime.text import MIMEText
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from deepgram import Deepgram
import aiohttp
import requests

app = FastAPI()

# Фейковая база данных кандидатов (в будущем заменим на реальную БД)
candidates_db = {}

# 1️⃣ Модель данных для регистрации кандидата
class Candidate(BaseModel):
    name: str
    email: str
    phone: str
    gender: str

# 2️⃣ Функция для отправки email через SMTP Яндекса
def send_email(to_email, interview_link):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.yandex.ru")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        raise HTTPException(status_code=500, detail="Ошибка: SMTP-настройки не заданы!")

    subject = "Ссылка на ваше интервью"
    body = f"Здравствуйте!\n\nВы зарегистрированы на интервью. Перейдите по ссылке: {interview_link}\n\nС уважением, AI-HR."

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)  # Используем SSL
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки email: {str(e)}")

# 3️⃣ API для регистрации кандидата
@app.post("/register/")
def register(candidate: Candidate):
    # Генерируем уникальный идентификатор интервью
    interview_id = str(uuid.uuid4())
    interview_link = f"https://ai-hr-project.onrender.com/interview/{interview_id}"

    # Сохраняем кандидата в "базу данных"
    candidates_db[interview_id] = {
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "gender": candidate.gender,
        "interview_link": interview_link
    }

    # Отправляем email кандидату
    send_email(candidate.email, interview_link)

    return {"message": "Кандидат зарегистрирован!", "interview_link": interview_link}

# 4️⃣ API для обработки аудио кандидата (Deepgram STT)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

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

# 5️⃣ API для генерации речи AI-HR (ElevenLabs TTS)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

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

# 6️⃣ API для проверки работоспособности сервера
@app.get("/")
def home():
    return {"message": "AI-HR API работает!"}
