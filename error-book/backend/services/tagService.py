import boto3
import uuid
from datetime import datetime, timezone
from typing import List
from boto3.dynamodb.conditions import Key
from models.tag import Tag, TagCreate, TagUpdate
from config import tableName, awsRegion

class TagService:
    def __init__(self):
        self.table = boto3.resource("dynamodb", region_name=awsRegion).Table(tableName)

    def create_tag(self, userId: str, data: TagCreate) -> Tag:
        tagId = str(uuid.uuid4())
        createdAt = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"USER#{userId}",
            "SK": f"TAG#{tagId}",
            "tagId": tagId,
            "userId": userId,
            "name": data.name,
            "color": data.color,
            "createdAt": createdAt,
        }
        self.table.put_item(Item=item)
        return Tag(**{k: v for k, v in item.items() if k in Tag.model_fields})

    def list_tags(self, userId: str) -> List[Tag]:
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{userId}") & Key("SK").begins_with("TAG#")
        )
        return [Tag(**{k: v for k, v in item.items() if k in Tag.model_fields})
                for item in resp["Items"]]

    def update_tag(self, userId: str, tagId: str, data: TagUpdate) -> Tag:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        names = {f"#{k}": k for k in updates}
        values = {f":{k}": v for k, v in updates.items()}
        resp = self.table.update_item(
            Key={"PK": f"USER#{userId}", "SK": f"TAG#{tagId}"},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        item = resp["Attributes"]
        return Tag(**{k: v for k, v in item.items() if k in Tag.model_fields})

    def delete_tag(self, userId: str, tagId: str) -> None:
        self.table.delete_item(Key={"PK": f"USER#{userId}", "SK": f"TAG#{tagId}"})
