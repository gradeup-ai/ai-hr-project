import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Получаем данные для SMTP из переменных окружения
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")  # SMTP-сервер (например, Gmail)
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  # Порт SMTP (обычно 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME")  # Логин (почта отправителя)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Пароль от почты (или API-ключ)
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)  # Почта отправителя

def send_interview_email(email_to, interview_link):
    """
    Отправка email с ссылкой на интервью.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Ошибка: SMTP_USERNAME или SMTP_PASSWORD не установлены!")
        return

    try:
        # Формируем email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = email_to
        msg["Subject"] = "Ваше интервью с AI HR"

        body = f"""
        <html>
        <body>
            <h2>Привет!</h2>
            <p>Вы зарегистрировались на интервью с AI HR.</p>
            <p><strong>Ваша ссылка для прохождения интервью:</strong></p>
            <p><a href="{interview_link}" target="_blank">{interview_link}</a></p>
            <p>Желаем удачи!</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        # Подключаемся к SMTP-серверу и отправляем email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Шифрование TLS
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, email_to, msg.as_string())
        server.quit()

        print(f"Email успешно отправлен на {email_to}")

    except Exception as e:
        print(f"Ошибка отправки email: {e}")
