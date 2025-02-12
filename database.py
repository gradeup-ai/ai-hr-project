import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Получение URL базы данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Переменная окружения DATABASE_URL не установлена! Убедитесь, что файл .env настроен.")

try:
    # Создание движка SQLAlchemy
    engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

    # Создание фабрики сессий
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Базовый класс для моделей
    Base = declarative_base()

except Exception as e:
    raise RuntimeError(f"Ошибка подключения к базе данных: {str(e)}")
