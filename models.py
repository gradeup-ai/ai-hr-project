import os
from sqlalchemy import create_engine, Column, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Подключение к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")  # URL для PostgreSQL на Render
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Определяем таблицы
class CandidateDB(Base):
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    interview_link = Column(String, nullable=False)

class InterviewDB(Base):
    __tablename__ = "interviews"
    
    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    status = Column(String, default="in_progress")
    questions = Column(Text, nullable=True)
    answers = Column(Text, nullable=True)
    report = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)

# Создаём таблицы в базе данных
Base.metadata.create_all(bind=engine)
