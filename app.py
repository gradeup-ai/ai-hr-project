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

client = OpenAI(api_key=OPENAI_API_KEY)

# 2️⃣ База данных кандидатов (в будущем заменим на реальную БД)
import json

# Файл для хранения данных
CANDIDATES_FILE = "candidates.json"

# Функция загрузки данных из файла
def load_candidates():
    try:
        with open(CANDIDATES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Функция сохранения данных в файл
def save_candidates():
    with open(CANDIDATES_FILE, "w", encoding="utf-8") as file:
        json.dump(candidates_db, file, indent=4, ensure_ascii=False)

# Загружаем кандидатов при старте
candidates_db = load_candidates()
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
    interview_id = str(uuid.uuid4())
    interview_link = f"https://ai-hr-project.onrender.com/interview/{interview_id}"

candidates_db[interview_id] = {
    "name": candidate.name,
    "email": candidate.email,
    "phone": candidate.phone,
    "gender": candidate.gender,
    "interview_link": interview_link
}

# Сохраняем кандидатов в файл после регистрации
save_candidates()


    send_email(candidate.email, interview_link)

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
    
    first_question = "Привет! Я Эмили, ваш виртуальный HR. Расскажите о своём опыте работы."
    interviews[interview_id]["questions"].append(first_question)

    return {"message": "Интервью началось", "question": first_question}

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
    if interview_id not in interviews:
        raise HTTPException(status_code=404, detail="Интервью не найдено")
    
    transcript = await transcribe_audio(audio_url)
    interviews[interview_id]["answers"].append(transcript)

    question = generate_next_question(interview_id, transcript)
    interviews[interview_id]["questions"].append(question)

    return {"question": question}

# 8️⃣ Функция генерации следующего вопроса (GPT-4o)
def generate_next_question(interview_id, last_answer):
    candidate = interviews[interview_id]["candidate"]

    prompt = f"""
Ты – AI-HR Эмили. Ты проводишь интервью с кандидатом {candidate['name']} на вакансию.
Твоя цель – объективно оценить его Hard и Soft Skills, анализируя его ответы.

1. Оцени его понимание **ключевых технических навыков** (Hard Skills), связанных с вакансией.
2. Проверяй **Soft Skills**: умение излагать мысли, аналитическое мышление, стрессоустойчивость, адаптивность.
3. Генерируй следующий вопрос на основе его ответа, углубляя оценку навыков.
4. Не давай подсказки. Собеседование должно проходить как реальный живой диалог.

Кандидат ответил: "{last_answer}".  
Какой будет следующий вопрос для глубокой оценки его квалификации?
"""


    response = client.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Ты – AI-HR, оцениваешь кандидата."},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]

# 9️⃣ API для завершения интервью и отчёта
@app.post("/interview/{interview_id}/finish")
def finish_interview(interview_id: str):
    if interview_id not in interviews:
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    report = generate_report(interview_id)
    interviews[interview_id]["status"] = "finished"

    return {"message": "Интервью завершено", "report": report}

# 🔟 Функция генерации отчёта (GPT-4o)
def generate_report(interview_id):
    candidate = interviews[interview_id]["candidate"]
    questions = interviews[interview_id]["questions"]
    answers = interviews[interview_id]["answers"]

    prompt = f"""
Сгенерируй **детальный отчёт** по собеседованию с кандидатом {candidate['name']}.

📌 **1. Основные данные кандидата**
- Имя: {candidate['name']}
- Email: {candidate['email']}
- Телефон: {candidate['phone']}
- Пол: {candidate['gender']}

📌 **2. Вопросы и ответы**  
**Вопросы** {questions}  
**Ответы** {answers}  

📌 **3. Оценка Hard Skills (Технические навыки)**  
- Определи ключевые технические навыки, требуемые для вакансии.
- Оцени уровень знаний по **5-балльной шкале** с детальным анализом.  
- Дай примеры из интервью, подтверждающие уровень владения каждым навыком.

📌 **4. Оценка Soft Skills (Личностные качества)**  
- Коммуникация: оцени, насколько ясно кандидат выражает мысли и взаимодействует.  
- Аналитическое мышление: оцени глубину анализа задач.  
- Стрессоустойчивость: как кандидат реагирует на сложные вопросы.  
- Самостоятельность: способен ли он решать задачи без чётких инструкций.  
- Готовность к обучению: как он адаптируется к новым темам.

📌 **5. Анализ эмоций и речи (Emotion AI)**  
- Определи **доминирующее настроение** кандидата: спокойный, уверенный, нервозный, агрессивный.  
- Как менялись его **эмоции в ходе собеседования**?  
- Реакция на сложные вопросы: были ли признаки волнения, раздражения, неуверенности?  
- Проанализируй **темп, громкость, паузы в речи** и как это влияет на восприятие.  

📌 **6. Итоговый вердикт AI-HR**  
- Подходит ли кандидат? **Да / Нет** (аргументированный вывод).  
- Сильные стороны кандидата.  
- Зоны роста и рекомендации.  
"""


    response = client.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Ты – AI-HR, создаёшь отчёт после интервью."},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]

# 1️⃣1️⃣ API для проверки сервера
@app.get("/")
def home():
    return {"message": "AI-HR API работает!"}
