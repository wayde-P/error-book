from pydantic import BaseModel
from typing import List, Optional

class QuestionCreate(BaseModel):
    imageKey: str
    subject: Optional[str] = None

class ManualQuestionCreate(BaseModel):
    subject: str
    content: str
    analysis: Optional[str] = None

class QuestionUpdate(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    analysis: Optional[str] = None
    tags: Optional[List[str]] = None

class Question(BaseModel):
    questionId: str
    userId: str
    imageKey: Optional[str] = None
    imageUrl: Optional[str] = None
    subject: str
    content: str
    analysis: str
    tags: List[str]
    status: str
    createdAt: str
