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
    if not GOOGLE_SHEETS_CREDENTIALS or not SPREADSHEET_ID:
        raise HTTPException(status_code=500, detail="Google Sheets credentials или SPREADSHEET_ID отсутствуют!")

    try:
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID)
        return sheet
    except gspread.exceptions.APIError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка Google Sheets API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Google Sheets: {str(e)}")


def get_or_create_worksheet(sheet, sheet_name, headers):
    """
    Получает лист в Google Sheets или создаёт новый, если он отсутствует.
    """
    try:
        worksheet = sheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols=str(len(headers)))
        worksheet.append_row(headers)
    return worksheet


def append_row_safe(worksheet, row_data):
    """
    Добавляет строку в лист, заменяя None на 'Нет данных'.
    """
    formatted_row = [cell if cell is not None else "Нет данных" for cell in row_data]
    
    try:
        worksheet.append_row(formatted_row)
    except gspread.exceptions.APIError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка Google Sheets API при записи: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при записи данных в Google Sheets: {str(e)}")


def save_candidate_to_google_sheets(candidate_id, name, email, phone, gender, interview_link):
    """
    Сохраняет данные о кандидате в лист 'Кандидаты'.
    """
    sheet = connect_google_sheets()
    headers = ["Candidate ID", "Name", "Email", "Phone", "Gender", "Interview Link"]
    worksheet = get_or_create_worksheet(sheet, SHEET_CANDIDATES, headers)

    append_row_safe(worksheet, [candidate_id, name, email, phone, gender, interview_link])


def save_interview_to_google_sheets(interview_id, candidate_id, status, questions, answers):
    """
    Сохраняет данные интервью в лист 'Интервью'.
    """
    sheet = connect_google_sheets()
    headers = ["Interview ID", "Candidate ID", "Status", "Questions", "Answers"]
    worksheet = get_or_create_worksheet(sheet, SHEET_INTERVIEWS, headers)

    append_row_safe(worksheet, [interview_id, candidate_id, status, questions, answers])


def save_report_to_google_sheets(interview_id, candidate_id, report):
    """
    Сохраняет отчёт по интервью в лист 'Отчёты'.
    """
    sheet = connect_google_sheets()
    headers = ["Interview ID", "Candidate ID", "Report"]
    worksheet = get_or_create_worksheet(sheet, SHEET_REPORTS, headers)

    append_row_safe(worksheet, [interview_id, candidate_id, report])


def save_video_to_google_sheets(interview_id, candidate_id, video_url):
    """
    Сохраняет ссылку на видеозапись интервью в лист 'Видео'.
    """
    sheet = connect_google_sheets()
    headers = ["Interview ID", "Candidate ID", "Video URL"]
    worksheet = get_or_create_worksheet(sheet, SHEET_VIDEOS, headers)

    append_row_safe(worksheet, [interview_id, candidate_id, video_url])


