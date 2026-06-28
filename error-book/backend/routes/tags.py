# backend/routes/tags.py
from fastapi import APIRouter, Depends, Request, HTTPException
from auth import get_current_user_id
from services.tagService import TagService
from models.tag import TagCreate, TagUpdate

router = APIRouter()

@router.get("")
def list_tags(request: Request, userId: str = Depends(get_current_user_id)):
    return TagService().list_tags(userId)

@router.post("")
def create_tag(data: TagCreate, request: Request, userId: str = Depends(get_current_user_id)):
    return TagService().create_tag(userId, data)

@router.put("/{tagId}")
def update_tag(tagId: str, data: TagUpdate, request: Request, userId: str = Depends(get_current_user_id)):
    return TagService().update_tag(userId, tagId, data)

@router.delete("/{tagId}")
def delete_tag(tagId: str, request: Request, userId: str = Depends(get_current_user_id)):
    TagService().delete_tag(userId, tagId)
    return {"message": "删除成功"}
