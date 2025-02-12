import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import HTTPException

# Переменные окружения
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_NAME = os.getenv("SHEET_NAME")


def connect_google_sheets():
    """
    Подключение к Google Sheets с использованием сервисного аккаунта.
    """
    if not GOOGLE_SHEETS_CREDENTIALS:
        raise HTTPException(status_code=500, detail="Google Sheets credentials отсутствуют!")

    try:
        # Загружаем JSON-ключ из переменной окружения
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)  
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict, 
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )

        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Google Sheets: {str(e)}")


def save_interview_to_google_sheets(interview_id, candidate_id, status, questions, answers, report, video_url):
    """
    Сохраняет данные интервью в Google Sheets.
    """
    sheet = connect_google_sheets()

    # Подготовка данных перед сохранением
    formatted_questions = questions if questions else "Нет данных"
    formatted_answers = answers if answers else "Нет данных"
    formatted_report = report if report else "Нет отчёта"
    formatted_video_url = video_url if video_url else "Видео не записано"

    try:
        sheet.append_row([
            interview_id, 
            candidate_id, 
            status, 
            formatted_questions, 
            formatted_answers, 
            formatted_report, 
            formatted_video_url
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при записи в Google Sheets: {str(e)}")
