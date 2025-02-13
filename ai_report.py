import os
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from database import SessionLocal  # Исправленный импорт
from models import InterviewDB
from fastapi import HTTPException
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# API ключи
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_REPORTS = os.getenv("SHEET_REPORTS")
SHEET_EMOTIONS = os.getenv("SHEET_EMOTIONS")

client = OpenAI(api_key=OPENAI_API_KEY)


# Функция подключения к Google Sheets
def connect_google_sheets(sheet_name):
    if not GOOGLE_SHEETS_CREDENTIALS:
        raise HTTPException(status_code=500, detail="Google Sheets credentials отсутствуют!")

    try:
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Google Sheets: {str(e)}")


# Функция генерации отчета
def generate_report(interview_id: str):
    session = SessionLocal()
    try:
        interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

        if not interview:
            raise HTTPException(status_code=404, detail="Интервью не найдено")

        questions = interview.questions if interview.questions else "Нет данных"
        answers = interview.answers if interview.answers else "Нет данных"

        # 📌 Подготовка промта для OpenAI
        prompt = f"""
Ты — AI-HR Эмили. Твоя задача — создать объективный отчёт по интервью с кандидатом.

📌 **1. Основные данные**
- Кандидат ID: {interview.candidate_id}
- Вопросы: {questions}
- Ответы: {answers}

📌 **2. Оценка Hard Skills**
- Насколько кандидат владеет техническими навыками?
- Проставь оценку по 5-балльной шкале и объясни.

📌 **3. Оценка Soft Skills**
- Насколько кандидат чётко излагает мысли?
- Как он реагирует на сложные вопросы?
- Аналитическое мышление, стрессоустойчивость, адаптивность.

📌 **4. Анализ эмоций и речи**
- Какие эмоции преобладали во время интервью?
- Динамика эмоций: стал ли кандидат напряжённым/расслабленным?
- Темп и громкость речи: как менялись?
- Были ли признаки волнения, уверенности?

📌 **5. Итоговый вердикт**
- Подходит ли кандидат? **Да / Нет** (обоснование).
- Какие сильные стороны?
- Какие зоны роста?
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Ты — AI-HR, анализируешь собеседование."},
                    {"role": "user", "content": prompt}
                ]
            )
            report_text = response.choices[0].message.content
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при генерации отчёта: {str(e)}")

        # 📌 Сохраняем отчёт в БД
        interview.report = report_text
        session.commit()

        try:
            # 📌 Сохранение отчета в Google Sheets
            sheet_reports = connect_google_sheets(SHEET_REPORTS)
            sheet_reports.append_row([
                interview_id,
                interview.candidate_id,
                questions,
                answers,
                report_text
            ])

            # 📌 Генерация анализа эмоций и речи
            prompt_emotions = f"""
Ты — AI-аналитик эмоций. Определи основные эмоции кандидата на основе его ответов.

📌 **Вопросы и ответы**
- Вопросы: {questions}
- Ответы: {answers}

1️⃣ Определи **основные эмоции** кандидата во время интервью.
2️⃣ Динамика эмоций: стал ли он более напряжённым / расслабленным?
3️⃣ Как менялись **темп и громкость речи**?
4️⃣ Были ли признаки волнения, уверенности?
"""

            response_emotions = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt_emotions}]
            )
            emotions_analysis = response_emotions.choices[0].message.content

            # 📌 Сохранение анализа эмоций в Google Sheets
            sheet_emotions = connect_google_sheets(SHEET_EMOTIONS)
            sheet_emotions.append_row([
                interview_id,
                interview.candidate_id,
                emotions_analysis
            ])

        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка записи в Google Sheets: {str(e)}")

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при работе с БД: {str(e)}")
    finally:
        session.close()

    return report_text
