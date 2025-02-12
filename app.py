import os
import smtplib
import uuid
import json
import gspread
from email.mime.text import MIMEText
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from deepgram import Deepgram
import aiohttp
import requests
from openai import OpenAI
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Определяем таблицы
class CandidateDB(Base):
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    interview_link = Column(String, nullable=False)

class InterviewDB(Base):
    __tablename__ = "interviews"
    
    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    status = Column(String, default="in_progress")
    questions = Column(Text)
    answers = Column(Text)
    report = Column(Text)
    video_url = Column(String, nullable=True)
    emotions_analysis = Column(Text, nullable=True)

# Создаём таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Переменные окружения
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.yandex.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_CANDIDATES = os.getenv("SHEET_CANDIDATES", "Кандидаты")
SHEET_INTERVIEWS = os.getenv("SHEET_INTERVIEWS", "Интервью")
SHEET_REPORTS = os.getenv("SHEET_REPORTS", "Отчёты")
SHEET_EMOTIONS = os.getenv("SHEET_EMOTIONS", "Анализ эмоций")

client = OpenAI(api_key=OPENAI_API_KEY)

# Подключение к Google Sheets
def connect_google_sheets():
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not credentials_json:
        raise HTTPException(status_code=500, detail="Google Sheets credentials отсутствуют!")
    creds_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, 
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    return client

# API для регистрации кандидата
@app.post("/register/")
def register(candidate: CandidateDB):
    session = SessionLocal()
    interview_id = str(uuid.uuid4())
    interview_link = f"https://ai-hr-project.onrender.com/interview/{interview_id}"

    new_candidate = CandidateDB(
        id=interview_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        gender=candidate.gender,
        interview_link=interview_link
    )
    session.add(new_candidate)
    session.commit()
    session.close()

    # Запись в Google Sheets
    client = connect_google_sheets()
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_CANDIDATES)
    sheet.append_row([candidate.name, candidate.email, candidate.phone, candidate.gender])

    return {"message": "Кандидат зарегистрирован!", "interview_link": interview_link}

# API для начала интервью
@app.get("/interview/{interview_id}")
def start_interview(interview_id: str):
    session = SessionLocal()
    candidate = session.query(CandidateDB).filter(CandidateDB.id == interview_id).first()
    session.close()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    return {"message": "Интервью началось", "question": "Привет! Я Эмили, ваш виртуальный HR. Расскажите о своём опыте работы."}

# API для завершения интервью и отчёта
@app.post("/interview/{interview_id}/finish")
def finish_interview(interview_id: str):
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    report = generate_report(interview_id)
    interview.report = report
    interview.status = "completed"
    session.commit()
    session.close()

    client = connect_google_sheets()
    sheet_interviews = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_INTERVIEWS)
    sheet_interviews.append_row([interview.id, interview.candidate_id, interview.status, interview.questions, interview.answers, interview.video_url])
    
    sheet_reports = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_REPORTS)
    sheet_reports.append_row([interview.id, interview.candidate_id, interview.status, interview.report])
    
    sheet_emotions = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_EMOTIONS)
    sheet_emotions.append_row([interview.id, interview.candidate_id, interview.emotions_analysis])

    return {"message": "Интервью завершено, отчёт сохранён"}

# Проверка сервера
@app.get("/")
def home():
    return {"message": "AI-HR API работает!"}

