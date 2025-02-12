import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import HTTPException

SHEET_NAME = os.getenv("SHEET_NAME")

def connect_google_sheets():
    """
    Устанавливает соединение с Google Sheets и возвращает объект таблицы.
    """
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if not credentials_json:
        raise HTTPException(status_code=500, detail="Google Sheets credentials отсутствуют!")

    try:
        creds_dict = json.loads(credentials_json)  # Преобразуем строку JSON в Python-объект
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, 
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])

        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Google Sheets: {str(e)}")
