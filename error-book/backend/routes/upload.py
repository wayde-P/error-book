# backend/routes/upload.py
import boto3
import uuid
from fastapi import APIRouter, Depends, Request, Query
from auth import get_current_user_id
from config import imagesBucket, awsRegion

router = APIRouter()

@router.get("/presigned-url")
def get_presigned_url(
    request: Request,
    filename: str = Query(...),
    contentType: str = Query(...),
    userId: str = Depends(get_current_user_id),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if contentType not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    questionId = str(uuid.uuid4())
    key = f"{userId}/{questionId}/{filename}"
    s3 = boto3.client("s3", region_name=awsRegion)
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": imagesBucket, "Key": key, "ContentType": contentType},
        ExpiresIn=900,
    )
    return {"url": url, "key": key, "questionId": questionId}
