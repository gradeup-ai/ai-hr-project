from pydantic import BaseModel, ConfigDict
from typing import Optional


class CandidateCreate(BaseModel):
    """
    Схема для регистрации кандидата.
    """
    name: str
    email: str
    phone: str
    gender: str


class CandidateResponse(BaseModel):
    """
    Схема ответа после регистрации кандидата.
    """
    id: str
    name: str
    email: str
    phone: str
    gender: str
    interview_link: str

    model_config = ConfigDict(from_attributes=True)  # Для корректной работы с SQLAlchemy


class InterviewResponse(BaseModel):
    """
    Схема ответа о начале интервью.
    """
    id: str
    candidate_id: str
    status: str
    questions: Optional[str] = None
    answers: Optional[str] = None
    report: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InterviewFinishResponse(BaseModel):
    """
    Схема ответа после завершения интервью.
    """
    message: str
    report: str
