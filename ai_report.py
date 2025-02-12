import os
from openai import OpenAI
from models import SessionLocal, InterviewDB
from fastapi import HTTPException

# Инициализируем клиент OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_report(interview_id: str):
    """
    Генерирует отчёт по собеседованию кандидата с помощью GPT-4o.
    """
    session = SessionLocal()
    interview = session.query(InterviewDB).filter(InterviewDB.id == interview_id).first()

    if not interview:
        session.close()
        raise HTTPException(status_code=404, detail="Интервью не найдено")

    # Генерируем аналитический отчёт
    prompt = f"""
Ты – AI-HR Эмили. Ты проводишь интервью с кандидатом {interview.candidate_id}.
Твоя цель – объективно оценить его Hard и Soft Skills, анализируя его ответы.

📌 **1. Вопросы и ответы**  
- Вопросы: {interview.questions if interview.questions else "Нет данных"}  
- Ответы: {interview.answers if interview.answers else "Нет данных"}  

📌 **2. Оценка Hard Skills**  
- Анализируй технические знания кандидата и сравнивай с требованиями вакансии.  
- Оцени уровень знаний по 5-балльной шкале и объясни, почему.  

📌 **3. Оценка Soft Skills**  
- Насколько кандидат ясно излагает мысли?  
- Как он реагирует на сложные вопросы?  
- Оцени стрессоустойчивость и способность к анализу.  

📌 **4. Итоговый вердикт**  
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
