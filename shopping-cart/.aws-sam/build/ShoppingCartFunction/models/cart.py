import os
import boto3
from decimal import Decimal


class CartModel:

    def __init__(self):
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(os.environ["CART_TABLE"])

    def get_items(self, session_id, list_type="cart"):
        response = self.table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("sessionId").eq(session_id)
        )
        return [
            self._serialize(item)
            for item in response["Items"]
            if item.get("listType", "cart") == list_type
        ]

    def get_wishlist_items(self, session_id):
        return self.get_items(session_id, list_type="wishlist")

    def get_item(self, session_id, product_id):
        response = self.table.get_item(
            Key={"sessionId": session_id, "productId": product_id}
        )
        item = response.get("Item")
        return self._serialize(item) if item else None

    def put_item(self, item):
        # DynamoDB rejects Python floats; convert to Decimal before writing.
        db_item = {}
        for key, val in item.items():
            if isinstance(val, float):
                db_item[key] = Decimal(str(val))
            elif isinstance(val, int) and not isinstance(val, bool):
                db_item[key] = val
            else:
                db_item[key] = val
        self.table.put_item(Item=db_item)

    def delete_item(self, session_id, product_id):
        self.table.delete_item(
            Key={"sessionId": session_id, "productId": product_id}
        )

    def clear(self, session_id):
        # DynamoDB has no bulk-delete API; items are removed one by one.
        # A Lambda timeout mid-loop will leave the cart partially cleared.
        items = self.get_items(session_id)
        for item in items:
            self.delete_item(session_id, item["productId"])

    def _serialize(self, item):
        if not item:
            return None
        result = {**item}
        if "price" in result:
            result["price"] = float(result["price"])
        if "quantity" in result:
            result["quantity"] = int(result["quantity"])
        return result
