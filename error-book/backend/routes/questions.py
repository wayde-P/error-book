# backend/routes/questions.py
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from typing import Optional, List
from auth import get_current_user_id
from services.questionService import QuestionService
from models.question import QuestionCreate, ManualQuestionCreate, QuestionUpdate, Question

router = APIRouter()

@router.post("/recognize")
def recognize_question(
    request: Request,
    data: QuestionCreate,
    userId: str = Depends(get_current_user_id),
) -> List[Question]:
    svc = QuestionService()
    return svc.create_questions_from_image(userId, data)

@router.post("/manual")
def create_manual_question(
    request: Request,
    data: ManualQuestionCreate,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    return svc.create_manual_question(userId, data)

@router.get("")
def list_questions(
    request: Request,
    tagId: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    lastKey: Optional[str] = Query(None),
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    return svc.list_questions(userId, tagId=tagId, keyword=keyword, lastKey=lastKey)

@router.get("/{questionId}")
def get_question(
    questionId: str,
    request: Request,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    try:
        return svc.get_question(userId, questionId)
    except KeyError:
        raise HTTPException(status_code=404, detail="题目不存在")

@router.put("/{questionId}")
def update_question(
    questionId: str,
    data: QuestionUpdate,
    request: Request,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    return svc.update_question(userId, questionId, data)

@router.delete("/{questionId}")
def delete_question(
    questionId: str,
    request: Request,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    svc.delete_question(userId, questionId)
    return {"message": "删除成功"}
