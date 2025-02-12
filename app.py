import os
import smtplib
import uuid

from email.mime.text import MIMEText
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from deepgram import Deepgram
import aiohttp
import requests
from openai import OpenAI
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")  # URL для PostgreSQL на Render

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

# Создаём таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 1️⃣ Переменные окружения
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
SHEET_NAME = os.getenv("SHEET_NAME")


client = OpenAI(api_key=OPENAI_API_KEY)

# 2️⃣ База данных кандидатов (в будущем заменим на реальную БД)
candidates_db = {}
interviews = {}

# 3️⃣ Модель данных кандидата
class Candidate(BaseModel):
    name: str
    email: str
    phone: str
    gender: str

# 4️⃣ Функция отправки email через Яндекс
def send_email(to_email, interview_link):
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        raise HTTPException(status_code=500, detail="Ошибка: SMTP-настройки не заданы!")

    subject = "Ссылка на ваше интервью"
    body = f"Здравствуйте!\n\nВы зарегистрированы на интервью. Перейдите по ссылке: {interview_link}\n\nС уважением, AI-HR."

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки email: {str(e)}")

# 5️⃣ API для регистрации кандидата
@app.post("/register/")
def register(candidate: Candidate):
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

    return {"message": "Кандидат зарегистрирован!", "interview_link": interview_link}

# 6️⃣ API для начала интервью
@app.get("/interview/{interview_id}")
def start_interview(interview_id: str):
    if interview_id not in candidates_db:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    
    candidate = candidates_db[interview_id]
    interviews[interview_id] = {
        "candidate": candidate,
        "questions": [],
        "answers": [],
        "status": "in_progress"
    }
    
    first_question = "Привет! Я Эмили, ваш виртуальный HR. Мы сейчас проведём интервью на позицию {job_title} ({job_level}) в компанию ВД КОМ. Я буду задавать вам вопросы, чтобы оценить ваши профессиональные навыки и личностные качества. Отвечайте подробно и искренне. Если что-то будет неясно – просто уточните у меня! Начнём с простого: расскажите о себе и вашем опыте работы."
    interviews[interview_id]["questions"].append(first_question)

    return {"message": "Интервью началось", "question": first_question}

@app.get("/livekit/{interview_id}")
def create_livekit_session(interview_id: str):
    session = SessionLocal()
    candidate = session.query(CandidateDB).filter(CandidateDB.id == interview_id).first()
    session.close()

    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    headers = {"Authorization": f"Bearer {LIVEKIT_API_KEY}"}
    response = requests.post("https://api.livekit.io/room", headers=headers, json={"name": interview_id})

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Ошибка создания сессии LiveKit")

    return response.json()

# 7️⃣ API для получения ответа кандидата (Deepgram STT)
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
async def process_answer(interview_id: str, audio_url: str):
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Распознаем голосовой ответ
    transcript = await transcribe_audio(audio_url)

    # Добавляем ответ в БД
    if interview.answers:
        interview.answers += f"\n{transcript}"
    else:
        interview.answers = transcript

    session.commit()
    session.close()

    # Генерируем следующий вопрос
    next_question = generate_next_question(interview_id, transcript)

    return {"next_question": next_question}


# 8️⃣ Функция генерации следующего вопроса (GPT-4o)
def generate_next_question(interview_id, last_answer):
    candidate = interviews[interview_id]["candidate"]

    prompt = f"""
Ты – AI-HR Эмили. Ты проводишь интервью с кандидатом {candidate['name']} на вакансию {job_title} ({job_level}) в компанию ВД КОМ.
Твоя цель – объективно оценить его Hard и Soft Skills, анализируя его ответы.Твоя задача – провести структурированное интервью, анализируя не только ответы кандидата, но и его голос, эмоции, стрессоустойчивость и невербальные сигналы.

1. Оцени его понимание **ключевых технических навыков** (Hard Skills), связанных с вакансией.
2. Проверяй **Soft Skills**: умение излагать мысли, аналитическое мышление - глубина анализа задач, стрессоустойчивость - реакция на сложные вопросы, адаптивность.
3. Генерируй следующий вопрос на основе его ответа, углубляя оценку навыков.
4. Не давай подсказки. Собеседование должно проходить как реальный живой диалог.
5. Интервью длится максимум 60 минут, ты можешь немного поторопить кандидата, если он затягивает ответы.
6. Сохраняй естественный стиль диалога, не превращай интервью в анкету.
Ты ведешь диалог в формате живого собеседования, не давая подсказок кандидату. Ты должен адаптировать тон и ритм вопросов в зависимости от состояния кандидата.

Голосовые и поведенческие параметры AI-рекрутера

✅ Стиль общения – дружелюбный, но формальный.
✅ Тон голоса – профессиональный, уверенный, энергичный.
✅ Скорость речи – средняя (не торопливая, но четкая).
✅ Интонация – вариативная, подчеркивающая важные моменты.
✅ Адаптация к эмоциям кандидата – если нервничает, успокаивать; если уверен, вести стандартное интервью

Кандидат ответил: "{last_answer}".  
Какой будет следующий вопрос для глубокой оценки его квалификации?
"""
"""
    response = client.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Ты – AI-HR, оцениваешь кандидата."},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]

import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def connect_google_sheets():
    # Загружаем JSON-ключ из переменной окружения
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if not credentials_json:
        raise HTTPException(status_code=500, detail="Google Sheets credentials отсутствуют!")

    creds_dict = json.loads(credentials_json)  # Преобразуем строку в JSON-объект
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, 
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

# 9️⃣ API для завершения интервью и отчёта
@app.post("/interview/{interview_id}/finish")
def finish_interview(interview_id: str):
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Генерируем отчёт AI-HR перед отправкой в таблицу
    report = generate_report(interview_id)
    interview.report = report

    # Записываем в Google Sheets
    sheet = connect_google_sheets()
    sheet.append_row([
        interview.id, 
        interview.candidate_id, 
        interview.status, 
        interview.questions if interview.questions else "Нет данных",
        interview.answers if interview.answers else "Нет данных",
        report, 
        interview.video_url if interview.video_url else "Видео не записано"
    ])

    interview.status = "completed"
    session.commit()
    session.close()

    return {"message": "Интервью завершено, отчёт сохранён"}

# 🔟 Функция генерации отчёта (GPT-4o)
def generate_report(interview_id: str):
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Генерируем аналитический отчёт
def generate_report(interview_id: str):
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Генерируем аналитический отчёт
    prompt = f"""
Сгенерируй детальный анализ по собеседованию с кандидатом {interview.candidate_id}.

**1. Вопросы и ответы**  
Вопросы: {interview.questions if interview.questions else "Нет данных"}  
Ответы: {interview.answers if interview.answers else "Нет данных"}  

**2. Оценка Hard Skills**  
- Анализируй технические знания кандидата и сравнивай с требованиями вакансии.  
- Оцени уровень знаний по 5-балльной шкале и объясни, почему.  

**3. Оценка Soft Skills**  
- Насколько кандидат ясно излагает мысли?  
- Как он реагирует на сложные вопросы?  
- Оцени стрессоустойчивость и способность к анализу.  

**4. Итоговый вердикт**  
- Подходит ли кандидат? **Да / Нет** (обоснование).  
- Какие сильные стороны?  
- Какие зоны роста?  
"""

    response = client.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Ты – AI-HR, оцениваешь кандидата."},
                  {"role": "user", "content": prompt}]
    )

    report_text = response.choices[0].message["content"]

    interview.report = report_text
    session.commit()
    session.close()

    return report_text

# 1️⃣1️⃣ API для проверки сервера
@app.get("/")
def home():
    return {"message": "AI-HR API работает!"}
