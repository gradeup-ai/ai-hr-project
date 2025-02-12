import uuid
import requests
import os
import aiohttp
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import SessionLocal, CandidateDB, InterviewDB
from schemas import CandidateCreate, CandidateResponse, InterviewResponse
from ai_report import generate_report
from google_sheets import save_interview_to_google_sheets
from deepgram import Deepgram
from openai import OpenAI

router = APIRouter()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 📺 1️⃣ **Регистрация кандидата**
@router.post("/register/", response_model=CandidateResponse)
def register(candidate: CandidateCreate, db: Session = Depends(get_db)):
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

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return CandidateResponse(
        id=new_candidate.id,
        name=new_candidate.name,
        email=new_candidate.email,
        phone=new_candidate.phone,
        gender=new_candidate.gender,
        interview_link=new_candidate.interview_link
    )


# 📺 2️⃣ **Начало интервью**
@router.get("/interview/{interview_id}", response_model=InterviewResponse)
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

# 📺 3️⃣ **Распознавание речи и анализ ответа**
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


@router.post("/interview/{interview_id}/answer")
async def process_answer(interview_id: str, audio_url: str, db: Session = Depends(get_db)):
    interview = db.query(InterviewDB).filter(InterviewDB.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    transcript = await transcribe_audio(audio_url)
    interview.answers = (interview.answers or "") + f"\n{transcript}"
    db.commit()
    db.refresh(interview)

    return {"message": "Ответ сохранён", "answer": transcript}


# 📺 4️⃣ **Сохранение видеозаписи интервью**
@router.post("/interview/{interview_id}/save_video")
def save_interview_video(interview_id: str, video_url: str, db: Session = Depends(get_db)):
    interview = db.query(InterviewDB).filter(InterviewDB.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    interview.video_url = video_url
    db.commit()
    db.refresh(interview)

    return {"message": "Видео интервью сохранено", "video_url": video_url}


# 📺 5️⃣ **Завершение интервью и генерация отчёта**
@router.post("/interview/{interview_id}/finish")
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
