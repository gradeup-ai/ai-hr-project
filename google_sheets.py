import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import HTTPException

# Переменные окружения
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Листы в Google Sheets
SHEET_CANDIDATES = "Кандидаты"
SHEET_INTERVIEWS = "Интервью"
SHEET_REPORTS = "Отчёты"
SHEET_VIDEOS = "Видео"


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
        sheet = client.open_by_key(SPREADSHEET_ID)
        return sheet
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Google Sheets: {str(e)}")


def save_candidate_to_google_sheets(candidate_id, name, email, phone, gender, interview_link):
    """
    Сохраняет данные о кандидате в лист 'Кандидаты'.
    """
    sheet = connect_google_sheets()

    try:
        worksheet = sheet.worksheet(SHEET_CANDIDATES)
        worksheet.append_row([candidate_id, name, email, phone, gender, interview_link])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при записи данных кандидата в Google Sheets: {str(e)}")


def save_interview_to_google_sheets(interview_id, candidate_id, status, questions, answers):
    """
    Сохраняет данные интервью в лист 'Интервью'.
    """
    sheet = connect_google_sheets()

    formatted_questions = questions if questions else "Нет данных"
    formatted_answers = answers if answers else "Нет данных"

    try:
        worksheet = sheet.worksheet(SHEET_INTERVIEWS)
        worksheet.append_row([interview_id, candidate_id, status, formatted_questions, formatted_answers])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при записи данных интервью в Google Sheets: {str(e)}")


def save_report_to_google_sheets(interview_id, candidate_id, report):
    """
    Сохраняет отчёт по интервью в лист 'Отчёты'.
    """
    sheet = connect_google_sheets()

    formatted_report = report if report else "Нет отчёта"

    try:
        worksheet = sheet.worksheet(SHEET_REPORTS)
        worksheet.append_row([interview_id, candidate_id, formatted_report])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при записи отчёта в Google Sheets: {str(e)}")


def save_video_to_google_sheets(interview_id, candidate_id, video_url):
    """
    Сохраняет ссылку на видеозапись интервью в лист 'Видео'.
    """
    sheet = connect_google_sheets()

    formatted_video_url = video_url if video_url else "Видео не записано"

    try:
        worksheet = sheet.worksheet(SHEET_VIDEOS)
        worksheet.append_row([interview_id, candidate_id, formatted_video_url])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при записи видео в Google Sheets: {str(e)}")
