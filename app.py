import os
import uuid
import requests
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import CandidateDB, InterviewDB
from schemas import CandidateCreate, CandidateResponse, InterviewResponse
from ai_report import generate_report
from google_sheets import save_interview_to_google_sheets
from deepgram import Deepgram
from openai import OpenAI
from send_email import send_interview_email  # Функция для отправки email

# Инициализация FastAPI
app = FastAPI(
    title="AI-HR Interview System",
    description="Система виртуального интервью с AI-HR Эмили",
    version="1.0.0"
)

# Разрешение CORS (для фронта)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешает запросы с любого домена
    allow_credentials=True,
    allow_methods=["*"],  # Разрешает все методы (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Разрешает все заголовки
)

# API ключи
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")  # Добавлен API ключ для email
client = OpenAI(api_key=OPENAI_API_KEY)

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Функция получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 📌 **Главная страница**
@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>Добро пожаловать в AI-HR Interview System!</h1><p>Перейдите в <a href='/docs'>/docs</a> для API документации.</p>"

# 📌 **1️⃣ Регистрация кандидата + Отправка email**
@app.post("/register/", response_model=CandidateResponse)
def register(candidate: CandidateCreate, db: Session = Depends(get_db)):
    interview_id = str(uuid.uuid4())
    interview_link = f"https://ai-hr-frontend.vercel.app/interview/{interview_id}"  # Исправленная ссылка на фронт

    new_candidate = CandidateDB(
        id=interview_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        gender=candidate.gender,
        interview_link=interview_link
    )

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    # Отправка email с ссылкой на интервью
    try:
        send_interview_email(candidate.email, interview_link)
    except Exception as e:
        print(f"Ошибка отправки email: {e}")

    return CandidateResponse(
        id=new_candidate.id,
        name=new_candidate.name,
        email=new_candidate.email,
        phone=new_candidate.phone,
        gender=new_candidate.gender,
        interview_link=new_candidate.interview_link
    )

# 📌 **2️⃣ Начало интервью**
@app.get("/interview/{interview_id}", response_model=InterviewResponse)
def start_interview(interview_id: str, db: Session = Depends(get_db)):
    candidate = db.query(CandidateDB).filter(CandidateDB.id == interview_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    first_question = (
        f"Здравствуйте, {candidate.name}! Я — Эмили, виртуальный HR. "
        f"Мы сейчас проведём интервью на позицию. "
        f"Я буду задавать вам вопросы, чтобы оценить ваши профессиональные навыки и личностные качества. "
        f"Отвечайте подробно и искренне. Если что-то будет неясно – просто уточните у меня! "
        f"Начнём с простого: расскажите о себе и вашем опыте работы."
    )

    interview = InterviewDB(
        id=interview_id,
        candidate_id=candidate.id,
        status="in_progress",
        questions=first_question
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    return InterviewResponse(
        id=interview.id,
        candidate_id=interview.candidate_id,
        status=interview.status,
        questions=interview.questions,
        answers=interview.answers,
        report=interview.report
    )

# 📌 **3️⃣ Распознавание речи (Deepgram)**
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

@app.post("/interview/{interview_id}/answer")
async def process_answer(interview_id: str, audio_url: str, db: Session = Depends(get_db)):
    interview = db.query(InterviewDB).filter(InterviewDB.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    transcript = await transcribe_audio(audio_url)
    interview.answers = (interview.answers or "") + f"\n{transcript}"
    db.commit()
    db.refresh(interview)

    return {"message": "Ответ сохранён", "answer": transcript}

# 📌 **4️⃣ Завершение интервью и генерация отчёта**
@app.post("/interview/{interview_id}/finish")
def finish_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = db.query(InterviewDB).filter(InterviewDB.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    report = generate_report(interview_id)
    interview.report = report
    interview.status = "completed"
    db.commit()
    db.refresh(interview)

    save_interview_to_google_sheets(interview.id, interview.candidate_id, interview.status, interview.questions, interview.answers, report, interview.video_url)

    return {"message": "Интервью завершено, отчёт сохранён"}

# 📌 **Запуск сервера**
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

