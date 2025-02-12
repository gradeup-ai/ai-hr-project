from pydantic import BaseModel
from typing import Optional

class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: str
    gender: str

class CandidateResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    gender: str
    interview_link: str

    class Config:
        from_attributes = True  # Чтобы FastAPI корректно преобразовывал SQLAlchemy -> Pydantic

class InterviewResponse(BaseModel):
    id: str
    candidate_id: str
    status: str
    questions: Optional[str]
    answers: Optional[str]
    report: Optional[str]

    class Config:
        from_attributes = True

