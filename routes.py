import uuid
import requests
from fastapi import APIRouter, HTTPException
from models import SessionLocal, CandidateDB, InterviewDB
from ai_report import generate_report
from google_sheets import save_to_google_sheets
from deepgram import Deepgram
import aiohttp
import os

router = APIRouter()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")


# 📌 1️⃣ **Регистрация кандидата**
@router.post("/register/")
def register(candidate: CandidateDB):
    """
    Регистрирует кандидата и создаёт ссылку на интервью.
    """
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


# 📌 2️⃣ **Начало интервью**
@router.get("/interview/{interview_id}")
def start_interview(interview_id: str):
    """
    Начинает интервью для кандидата.
    """
    session = SessionLocal()
    candidate = session.query(CandidateDB).filter(CandidateDB.id == interview_id).first()
    session.close()

    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    first_question = "Привет! Я Эмили, ваш виртуальный HR. Расскажите о своём опыте работы."

    return {"message": "Интервью началось", "question": first_question}


# 📌 3️⃣ **Создание видеозвонка (LiveKit)**
@router.get("/livekit/{interview_id}")
def create_livekit_session(interview_id: str):
    """
    Создаёт видеозвонок в LiveKit.
    """
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


# 📌 4️⃣ **Распознавание речи и анализ ответа (Deepgram + OpenAI)**
async def transcribe_audio(audio_url: str):
    """
    Распознаёт речь кандидата с помощью Deepgram.
    """
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=500, detail="Deepgram API key отсутствует!")

    deepgram = Deepgram(DEEPGRAM_API_KEY)
    async with aiohttp.ClientSession() as session:
        response = await deepgram.transcription.prerecorded(
            {"url": audio_url},
            {"punctuate": True, "language": "ru"}
        )
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]


@router.post("/interview/{interview_id}/answer")
async def process_answer(interview_id: str, audio_url: str):
    """
    Обрабатывает ответ кандидата: распознаёт речь, анализирует ответ и генерирует следующий вопрос.
    """
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    transcript = await transcribe_audio(audio_url)

    if interview.answers:
        interview.answers += f"\n{transcript}"
    else:
        interview.answers = transcript

    session.commit()
    session.close()

    next_question = generate_next_question(interview_id, transcript)

    return {"next_question": next_question}


# 📌 5️⃣ **Сохранение видеозаписи интервью**
@router.post("/interview/{interview_id}/save_video")
def save_interview_video(interview_id: str, video_url: str):
    """
    Сохраняет ссылку на видеозапись интервью.
    """
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    interview.video_url = video_url
    session.commit()
    session.close()

    return {"message": "Видео интервью сохранено", "video_url": video_url}


# 📌 6️⃣ **Завершение интервью и генерация отчёта**
@router.post("/interview/{interview_id}/finish")
def finish_interview(interview_id: str):
    """
    Завершает интервью, создаёт отчёт и загружает его в Google Sheets.
    """
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Генерация отчёта AI-HR
    report = generate_report(interview_id)
    interview.report = report

    # Сохранение данных в Google Sheets
    save_to_google_sheets([
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
