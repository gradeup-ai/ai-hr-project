import os
import uuid
import requests
import jwt
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import CandidateDB, InterviewDB
from schemas import CandidateCreate, CandidateResponse, InterviewResponse
from ai_report import generate_report
from google_sheets import save_interview_to_google_sheets
from deepgram import Deepgram
from openai import OpenAI
from send_email import send_interview_email
from fastapi.middleware.cors import CORSMiddleware

# Инициализация FastAPI
app = FastAPI(
    title="AI-HR Interview System",
    description="Система виртуального интервью с AI-HR Эмили",
    version="1.0.0"
)

# Разрешение CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-hr-frontend.onrender.com"],  # Разрешаем доступ только с фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ключи
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_SERVER_URL = os.getenv("LIVEKIT_SERVER_URL")  # Переменная окружения для LiveKit URL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")  # URL фронтенда

client = OpenAI(api_key=OPENAI_API_KEY)

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>Добро пожаловать в AI-HR Interview System!</h1><p>Перейдите в <a href='/docs'>/docs</a> для API документации.</p>"

@app.post("/register/", response_model=CandidateResponse)
def register(candidate: CandidateCreate, db: Session = Depends(get_db)):
    interview_id = str(uuid.uuid4())
    interview_link = f"{FRONTEND_URL}/interview/{interview_id}"

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

    send_interview_email(candidate.email, interview_link)

    return CandidateResponse(
        id=new_candidate.id,
        name=new_candidate.name,
        email=new_candidate.email,
        phone=new_candidate.phone,
        gender=new_candidate.gender,
        interview_link=new_candidate.interview_link
    )

@app.get("/interview/{interview_id}", response_model=InterviewResponse)
def start_interview(interview_id: str, db: Session = Depends(get_db)):
    candidate = db.query(CandidateDB).filter(CandidateDB.id == interview_id).first()
    interview = db.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    if interview:
        return InterviewResponse(
            id=interview.id,
            candidate_id=interview.candidate_id,
            status=interview.status,
            questions=interview.questions,
            answers=interview.answers,
            report=interview.report
        )

    first_question = (
        f"Здравствуйте, {candidate.name}! Я — Эмили, виртуальный HR. "
        f"Мы сейчас проведём интервью на позицию. "
        f"Отвечайте подробно и искренне. "
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

    save_interview_to_google_sheets(
        interview.id, interview.candidate_id, interview.status, 
        interview.questions, interview.answers, report, interview.video_url
    )

    return {"message": "Интервью завершено, отчёт сохранён"}

@app.get("/livekit/token/{interview_id}")
def get_livekit_token(interview_id: str, db: Session = Depends(get_db)):
    candidate = db.query(CandidateDB).filter(CandidateDB.id == interview_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    token = jwt.encode(
        {
            "exp": int(os.time() + 3600),
            "room": interview_id,
            "participant": candidate.id,
            "identity": candidate.name
        },
        LIVEKIT_API_SECRET,
        algorithm="HS256"
    )

    return {
        "url": f"{LIVEKIT_SERVER_URL}/room/{interview_id}",  # URL LiveKit для подключения
        "token": token
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
