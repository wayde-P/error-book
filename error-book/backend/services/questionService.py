import boto3
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from models.question import Question, QuestionCreate, QuestionUpdate
from services.recognition import RecognitionService
from config import tableName, imagesBucket, awsRegion


class QuestionService:
    def __init__(self):
        self.table = boto3.resource("dynamodb", region_name=awsRegion).Table(tableName)
        self.s3 = boto3.client("s3", region_name=awsRegion)
        self.recog = RecognitionService()

    def _presign(self, imageKey: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": imagesBucket, "Key": imageKey},
            ExpiresIn=3600,
        )

    def _item_to_question(self, item: dict) -> Question:
        return Question(
            questionId=item["questionId"],
            userId=item["userId"],
            imageKey=item["imageKey"],
            imageUrl=self._presign(item["imageKey"]),
            subject=item.get("subject", ""),
            content=item.get("content", ""),
            analysis=item.get("analysis", ""),
            tags=item.get("tags", []),
            status=item["status"],
            createdAt=item["createdAt"],
        )

    def create_question(self, userId: str, data: QuestionCreate) -> Question:
        questionId = str(uuid.uuid4())
        createdAt = datetime.now(timezone.utc).isoformat()
        status = "done"
        subject, content, analysis = data.subject or "", "", ""
        try:
            result = self.recog.recognize(data.imageKey)
            subject = result.get("subject", subject)
            content = result.get("content", "")
            analysis = result.get("analysis", "")
        except Exception:
            status = "failed"

        item = {
            "PK": f"USER#{userId}",
            "SK": f"QUESTION#{questionId}",
            "questionId": questionId,
            "userId": userId,
            "imageKey": data.imageKey,
            "subject": subject,
            "content": content,
            "analysis": analysis,
            "tags": [],
            "status": status,
            "createdAt": createdAt,
        }
        for attempt in range(3):
            try:
                self.table.put_item(Item=item)
                break
            except Exception:
                if attempt == 2:
                    raise
        return self._item_to_question(item)

    def list_questions(self, userId: str, tagId: Optional[str], keyword: Optional[str], lastKey: Optional[str]) -> dict:
        import json
        import base64
        from boto3.dynamodb.conditions import Key

        kwargs: dict = {}
        if lastKey:
            kwargs["ExclusiveStartKey"] = json.loads(base64.b64decode(lastKey))

        if tagId:
            resp = self.table.query(
                IndexName="TagIndex",
                KeyConditionExpression=Key("tagPK").eq(f"USER#{userId}#TAG#{tagId}"),
                **kwargs,
            )
        elif keyword:
            resp = self.table.query(
                IndexName="ContentIndex",
                KeyConditionExpression=Key("PK").eq(f"USER#{userId}") & Key("content").begins_with(keyword),
                **kwargs,
            )
        else:
            resp = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"USER#{userId}") & Key("SK").begins_with("QUESTION#"),
                ScanIndexForward=False,
                **kwargs,
            )

        nextKey = None
        if "LastEvaluatedKey" in resp:
            nextKey = base64.b64encode(json.dumps(resp["LastEvaluatedKey"]).encode()).decode()

        return {"items": [self._item_to_question(i) for i in resp["Items"]], "nextKey": nextKey}

    def get_question(self, userId: str, questionId: str) -> Question:
        resp = self.table.get_item(Key={"PK": f"USER#{userId}", "SK": f"QUESTION#{questionId}"})
        item = resp.get("Item")
        if not item:
            raise KeyError(f"Question {questionId} not found")
        return self._item_to_question(item)

    def update_question(self, userId: str, questionId: str, data: QuestionUpdate) -> Question:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        names = {f"#{k}": k for k in updates}
        values = {f":{k}": v for k, v in updates.items()}
        resp = self.table.update_item(
            Key={"PK": f"USER#{userId}", "SK": f"QUESTION#{questionId}"},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return self._item_to_question(resp["Attributes"])

    def delete_question(self, userId: str, questionId: str) -> None:
        self.table.delete_item(Key={"PK": f"USER#{userId}", "SK": f"QUESTION#{questionId}"})
