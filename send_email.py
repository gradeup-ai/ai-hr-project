import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Получаем данные для SMTP из переменных окружения
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.yandex.com")  # SMTP-сервер Яндекса
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))  # Яндекс использует порт 465 (SSL)
SMTP_USERNAME = os.getenv("SMTP_USERNAME")  # Логин (почта отправителя)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Пароль от почты (API-ключ)
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)  # Почта отправителя

def send_interview_email(email_to, interview_link):
    """
    Отправка email с ссылкой на интервью через Яндекс.Почту.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Ошибка: SMTP_USERNAME или SMTP_PASSWORD не установлены!")
        return False

    try:
        # Формируем email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = email_to
        msg["Subject"] = "Ваше интервью с AI HR"

        body = f"""\
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

        # Подключаемся к Яндекс SMTP-серверу (используем SSL)
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, email_to, msg.as_string())

        print(f"✅ Email успешно отправлен на {email_to}")
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        return False

    finally:
        if 'server' in locals():
            server.quit()  # Закрываем соединение
