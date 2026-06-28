# backend/auth.py
from fastapi import Request, HTTPException

def get_current_user_id(request: Request) -> str:
    # API Gateway JWT Authorizer 将 claims 注入 requestContext
    ctx = request.scope.get("aws.event", {})
    try:
        userId = ctx["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    except (KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return userId
