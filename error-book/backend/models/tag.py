from pydantic import BaseModel
from typing import Optional

class TagCreate(BaseModel):
    name: str
    color: str             # hex 颜色，如 "#FF5733"

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class Tag(BaseModel):
    tagId: str
    userId: str
    name: str
    color: str
    createdAt: str
