import uuid
from datetime import datetime, timezone
from models.order import OrderModel
from config import TAX_RATE


class OrderService:

    def __init__(self):
        """Initialize OrderService with the order model."""
        self.model = OrderModel()

    def create_order(self, session_id, items, subtotal, shipping_address, discount=None):
        """Create and persist a new order, applying discount if provided. Returns the order dict."""
        orderId = str(uuid.uuid4())[:8]

        if discount:
            discountAmount = discount["discountAmount"]
            discountedSubtotal = max(0.0, round(subtotal - discountAmount, 2))
            tax = round(discountedSubtotal * float(TAX_RATE), 2)
            total = round(discountedSubtotal + tax, 2)
        else:
            discountAmount = 0.0
            tax = round(subtotal * float(TAX_RATE), 2)
            total = round(subtotal + tax, 2)

        order = {
            "sessionId": session_id,
            "orderId": orderId,
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
            order["discountAmount"] = str(discountAmount)

        self.model.put(order)
        return order

    def get_orders(self, session_id):
        """Return all orders for session_id."""
        return self.model.get_by_session(session_id)

    def get_order(self, session_id, order_id):
        """Return a single order by session_id and order_id."""
        return self.model.get(session_id, order_id)
