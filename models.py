from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from database import Base

class CandidateDB(Base):
    """
    Таблица кандидатов
    """
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    interview_link = Column(String, nullable=False)
    
    interviews = relationship("InterviewDB", back_populates="candidate")


class InterviewDB(Base):
    """
    Таблица интервью
    """
    __tablename__ = "interviews"
    
    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    status = Column(String, default="in_progress")
    questions = Column(Text, nullable=True)
    answers = Column(Text, nullable=True)
    report = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)
    
    candidate = relationship("CandidateDB", back_populates="interviews")
