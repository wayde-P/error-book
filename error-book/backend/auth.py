# backend/auth.py
from fastapi import Request, HTTPException

def get_current_user_id(request: Request) -> str:
    ctx = request.scope.get("aws.event", {})
    try:
        # REST API + Cognito User Pool Authorizer
        claims = ctx["requestContext"]["authorizer"]["claims"]
        userId = claims["sub"]
    except (KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return userId
