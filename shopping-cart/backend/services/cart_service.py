from decimal import Decimal
from models.cart import CartModel
from services.product_service import ProductService
from services.discount_service import DiscountService
from config import TAX_RATE


class CartService:

    def __init__(self):
        """Initialize CartService with cart model, product service, and discount service."""
        self.model = CartModel()
        self.product_service = ProductService()
        self.discount_service = DiscountService()

    TAX_RATE = TAX_RATE
    FREE_SHIPPING_THRESHOLD = Decimal("50.00")
    SHIPPING_COST = Decimal("5.99")

    def _calculate_tax(self, subtotal: Decimal) -> tuple[float, float]:
        """Returns (tax, total) for the given subtotal."""
        return float(subtotal * self.TAX_RATE), float(subtotal * (1 + self.TAX_RATE))

    def _calculate_shipping(self, subtotal: Decimal) -> float:
        """Returns shipping cost: free when subtotal >= FREE_SHIPPING_THRESHOLD, else SHIPPING_COST."""
        if subtotal >= self.FREE_SHIPPING_THRESHOLD:
            return 0.0
        return float(self.SHIPPING_COST)

    def get_cart(self, session_id, discount=None):
        """Return the cart contents for session_id, optionally applying a discount code."""
        items = self.model.get_items(session_id)
        subtotal = sum(
            Decimal(str(item["price"])) * int(item["quantity"]) for item in items
        )
        item_count = sum(int(item["quantity"]) for item in items)
        tax, total = self._calculate_tax(subtotal)

        cart = {
            "items": items,
            "itemCount": item_count,
            "subtotal": float(subtotal),
            "tax": tax,
            "total": total,
        }

        return self.discount_service.apply_to_cart(cart, discount)

    def add_item(self, session_id, product_id, quantity=1):
        """Add product_id to the cart for session_id, incrementing quantity if already present."""
        product = self.product_service.get_by_id(product_id)
        if not product:
            return {"error": "Product not found"}

        existing = self.model.get_item(session_id, product_id)
        if existing:
            new_quantity = int(existing["quantity"]) + quantity
        else:
            new_quantity = quantity

        # Snapshot name/price/image from the product at add-time so cart
        # totals stay stable if the product is updated or deleted later.
        cart_item = {
            "sessionId": session_id,
            "productId": product_id,
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "quantity": new_quantity,
            "listType": "cart",
        }
        self.model.put_item(cart_item)

        return {
            "message": f"Added {product['name']} to cart",
            "item": cart_item,
        }

    def update_quantity(self, session_id, product_id, quantity):
        """Update the quantity of product_id in the cart for session_id."""
        existing = self.model.get_item(session_id, product_id)
        if not existing:
            return {"error": "Item not in cart"}

        existing["quantity"] = quantity
        self.model.put_item(existing)
        return {"message": "Quantity updated", "item": existing}

    def remove_item(self, session_id, product_id):
        """Remove product_id from the cart for session_id."""
        existing = self.model.get_item(session_id, product_id)
        if not existing:
            return {"error": "Item not in cart"}

        self.model.delete_item(session_id, product_id)
        return {"message": f"Removed {existing['name']} from cart"}

    def clear_cart(self, session_id):
        """Remove all items from the cart for session_id."""
        self.model.clear(session_id)
