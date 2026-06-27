import os
import boto3
from decimal import Decimal


class DiscountModel:

    def __init__(self):
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(os.environ["DISCOUNTS_TABLE"])

    def get(self, code: str):
        response = self.table.get_item(Key={"code": code.upper()})
        item = response.get("Item")
        return self._serialize(item) if item else None

    def increment_used_count(self, code: str):
        """Atomically increment usedCount. Called once per successful order."""
        self.table.update_item(
            Key={"code": code.upper()},
            UpdateExpression="SET usedCount = if_not_exists(usedCount, :zero) + :one",
            ExpressionAttributeValues={":zero": 0, ":one": 1},
        )

    def _serialize(self, item):
        if not item:
            return None
        result = {**item}
        if "value" in result:
            result["value"] = float(result["value"])
        if "maxUses" in result:
            result["maxUses"] = int(result["maxUses"])
        if "usedCount" in result:
            result["usedCount"] = int(result["usedCount"])
        return result
