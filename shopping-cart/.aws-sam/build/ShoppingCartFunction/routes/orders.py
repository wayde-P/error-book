from flask import Blueprint, jsonify, request
from services.order_service import OrderService
from services.cart_service import CartService
from services.discount_service import DiscountService

orders_bp = Blueprint("orders", __name__)
order_service = OrderService()
cart_service = CartService()
discount_service = DiscountService()

# Hardcoded for the workshop — see routes/cart.py for context.
SESSION_ID = "workshop-user"


@orders_bp.route("", methods=["POST"])
def create_order():
    body = request.get_json() or {}
    shipping_address = body.get("shippingAddress")

    if not shipping_address:
        return jsonify({"error": "shippingAddress is required"}), 400

    cart = cart_service.get_cart(SESSION_ID)
    if not cart["items"]:
        return jsonify({"error": "Cart is empty"}), 400

    # Re-validate discount at checkout time to guard against codes expiring
    # between the cart page and order submission.
    discount_code = body.get("discountCode")
    discount = None
    if discount_code:
        discount = discount_service.validate(discount_code, cart["subtotal"])

    order = order_service.create_order(
        session_id=SESSION_ID,
        items=cart["items"],
        subtotal=cart["subtotal"],
        shipping_address=shipping_address,
        discount=discount,
    )

    # Clear cart here rather than inside OrderService — cart management is an
    # HTTP-layer concern, not part of the order domain itself. Note: if this
    # call fails after the order is saved the cart will not be cleared.
    cart_service.clear_cart(SESSION_ID)

    # Increment usedCount after order is persisted and cart is cleared.
    if discount:
        discount_service.consume(discount["code"])

    return jsonify(order), 201


@orders_bp.route("", methods=["GET"])
def list_orders():
    orders = order_service.get_orders(SESSION_ID)
    return jsonify({"orders": orders, "count": len(orders)})


@orders_bp.route("/<order_id>", methods=["GET"])
def get_order(order_id):
    order = order_service.get_order(SESSION_ID, order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)
