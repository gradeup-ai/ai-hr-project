from pydantic import BaseModel
from typing import Optional

class CandidateBase(BaseModel):
    name: str
    email: str
    phone: str
    gender: str

class CandidateCreate(CandidateBase):
    pass  # Используется для создания кандидата

class CandidateResponse(CandidateBase):
    id: str
    interview_link: str

    class Config:
        orm_mode = True

class InterviewBase(BaseModel):
    candidate_id: str
    status: str
    questions: Optional[str] = None
    answers: Optional[str] = None
    report: Optional[str] = None
    video_url: Optional[str] = None

class InterviewResponse(InterviewBase):
    id: str

    class Config:
        orm_mode = True
