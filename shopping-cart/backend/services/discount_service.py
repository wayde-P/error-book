from datetime import datetime, timezone
from decimal import Decimal
from models.discount import DiscountModel


class DiscountService:

    def __init__(self):
        self.model = DiscountModel()

    def validate(self, code: str, subtotal: float):
        """Return discount dict with discountAmount, or None if invalid/expired/exhausted."""
        record = self.model.get(code.upper())
        if not record:
            return None

        # Check expiry
        expires_at = record.get("expiresAt")
        if expires_at:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                return None

        # Check usage cap (0 = unlimited)
        max_uses = record.get("maxUses", 0)
        if max_uses and int(record.get("usedCount", 0)) >= max_uses:
            return None

        discount_amount = self.calculate_discount(record, subtotal)
        return {
            "code": record["code"],
            "type": record["type"],
            "value": record["value"],
            "discountAmount": discount_amount,
        }

    def calculate_discount(self, discount: dict, subtotal: float) -> float:
        dtype = discount.get("type")
        value = float(discount.get("value", 0))
        if dtype == "percent":
            if not (0 <= value <= 100):
                raise ValueError(f"Percent discount value must be 0–100, got {value}")
            amount = round(subtotal * value / 100, 2)
        elif dtype == "fixed":
            if value < 0:
                raise ValueError(f"Fixed discount value must be non-negative, got {value}")
            amount = min(value, subtotal)
        else:
            raise ValueError(f"Unknown discount type: {dtype!r}")
        return amount

    def consume(self, code: str):
        """Increment usedCount after a successful order. Call once per order."""
        self.model.increment_used_count(code)

    def apply_to_cart(self, cart: dict, discount) -> dict:
        """Inject discount totals into a cart dict. Returns cart unchanged if discount is None."""
        if not discount:
            return cart

        subtotal = cart["subtotal"]
        discount_amount = discount["discountAmount"]
        discounted_subtotal = max(0.0, round(subtotal - discount_amount, 2))
        tax = round(discounted_subtotal * 0.08, 2)
        total = round(discounted_subtotal + tax, 2)

        cart["discountCode"] = discount["code"]
        cart["discountAmount"] = discount_amount
        cart["discountedSubtotal"] = discounted_subtotal
        cart["tax"] = tax
        cart["total"] = total
        return cart
