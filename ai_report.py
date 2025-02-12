import os
from openai import OpenAI
from sqlalchemy.orm import Session
from models import SessionLocal, InterviewDB
from fastapi import HTTPException

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def generate_report(interview_id: str):
    """
    Генерирует детальный отчёт по интервью кандидата.
    """
    session = SessionLocal()
    
    # Получаем данные об интервью из БД
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        session.close()
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Подготовка данных для OpenAI
    questions = interview.questions if interview.questions else "Нет данных"
    answers = interview.answers if interview.answers else "Нет данных"

    prompt = f"""
Ты — AI-HR Эмили. Твоя задача — создать объективный отчёт по интервью с кандидатом.

📌 **1. Вопросы и ответы**
- Вопросы: {questions}
- Ответы: {answers}

📌 **2. Оценка Hard Skills**
- Определи, насколько кандидат владеет необходимыми техническими навыками.
- Проставь оценку по 5-балльной шкале и объясни.

📌 **3. Оценка Soft Skills**
- Оцени, насколько кандидат чётко излагает мысли.
- Оцени реакцию на сложные вопросы (стрессоустойчивость, аналитическое мышление).

📌 **4. Итоговый вердикт**
- Подходит ли кандидат? **Да / Нет** (обоснование).
- Какие сильные стороны?
- Какие зоны роста?
"""

    try:
        response = client.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты — AI-HR, анализируешь собеседование."},
                {"role": "user", "content": prompt}
            ]
        )
        report_text = response.choices[0].message["content"]
    except Exception as e:
        session.close()
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации отчёта: {str(e)}")

    # Сохраняем отчёт в БД
    interview.report = report_text
    session.commit()
    session.close()

    return report_text
