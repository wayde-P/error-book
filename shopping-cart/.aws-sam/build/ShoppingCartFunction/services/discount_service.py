from datetime import datetime, timezone
from decimal import Decimal
from models.discount import DiscountModel
from config import TAX_RATE


class DiscountService:

    def __init__(self):
        """Initialize DiscountService with the discount model."""
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
        maxUses = record.get("maxUses", 0)
        if maxUses and int(record.get("usedCount", 0)) >= maxUses:
            return None

        discountAmount = self.calculate_discount(record, subtotal)
        return {
            "code": record["code"],
            "type": record["type"],
            "value": record["value"],
            "discountAmount": discountAmount,
        }

    def calculate_discount(self, discount: dict, subtotal: float) -> float:
        """Calculate and return the discount amount for the given discount record and subtotal."""
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
        discountAmount = discount["discountAmount"]
        discountedSubtotal = max(0.0, round(subtotal - discountAmount, 2))
        tax = round(discountedSubtotal * float(TAX_RATE), 2)
        total = round(discountedSubtotal + tax, 2)

        cart["discountCode"] = discount["code"]
        cart["discountAmount"] = discountAmount
        cart["discountedSubtotal"] = discountedSubtotal
        cart["tax"] = tax
        cart["total"] = total
        return cart
