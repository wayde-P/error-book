import uuid
from datetime import datetime, timezone
from models.order import OrderModel


class OrderService:

    def __init__(self):
        self.model = OrderModel()

    # Create a new order
    def create_order(self, session_id, items, subtotal, shipping_address, discount=None):
        order_id = str(uuid.uuid4())[:8]

        if discount:
            discount_amount = discount["discountAmount"]
            discounted_subtotal = max(0.0, round(subtotal - discount_amount, 2))
            tax = round(discounted_subtotal * 0.08, 2)
            total = round(discounted_subtotal + tax, 2)
        else:
            discount_amount = 0.0
            tax = round(subtotal * 0.08, 2)
            total = round(subtotal + tax, 2)

        order = {
            "sessionId": session_id,
            "orderId": order_id,
            "items": items,
            "subtotal": str(subtotal),
            "tax": str(tax),
            "total": str(total),
            "shippingAddress": shipping_address,
            "status": "confirmed",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        if discount:
            order["discountCode"] = discount["code"]
            order["discountAmount"] = str(discount_amount)

        self.model.put(order)
        return order

    def get_orders(self, session_id):
        return self.model.get_by_session(session_id)

    def get_order(self, session_id, order_id):
        return self.model.get(session_id, order_id)
