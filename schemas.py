from pydantic import BaseModel
from typing import Optional


# 📌 **Схема для регистрации кандидата**
class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: str
    gender: str


# 📌 **Схема ответа при регистрации кандидата**
class CandidateResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    gender: str
    interview_link: str

    class Config:
        orm_mode = True


# 📌 **Схема интервью**
class InterviewResponse(BaseModel):
    id: str
    candidate_id: str
    status: str
    questions: Optional[str] = None
    answers: Optional[str] = None
    report: Optional[str] = None

    class Config:
        orm_mode = True
