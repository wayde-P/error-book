from pydantic import BaseModel
from typing import List, Optional

class QuestionCreate(BaseModel):
    imageKey: str          # S3 object key，格式 {userId}/{questionId}/{filename}
    subject: Optional[str] = None

class QuestionUpdate(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    analysis: Optional[str] = None
    tags: Optional[List[str]] = None

class Question(BaseModel):
    questionId: str
    userId: str
    imageKey: str
    imageUrl: str          # S3 presigned GET URL，供前端展示
    subject: str
    content: str
    analysis: str
    tags: List[str]
    status: str            # pending / done / failed
    createdAt: str
