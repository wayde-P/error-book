from flask import Blueprint, jsonify, request
from services.cart_service import CartService
from services.discount_service import DiscountService

cart_bp = Blueprint("cart", __name__)
cart_service = CartService()
discount_service = DiscountService()

# Hardcoded for the workshop — in production replace with a real identity
# (e.g. JWT sub or Cognito user ID) so each user gets an isolated cart.
SESSION_ID = "workshop-user"


@cart_bp.route("", methods=["GET"])
def get_cart():
    code = request.args.get("code")
    discount = None
    if code:
        # Pre-fetch cart subtotal to calculate discount amount
        base_cart = cart_service.get_cart(SESSION_ID)
        discount = discount_service.validate(code, base_cart["subtotal"])
    cart = cart_service.get_cart(SESSION_ID, discount=discount)
    return jsonify(cart)


@cart_bp.route("/items", methods=["POST"])
def add_item():
    body = request.get_json()
    if not body or "productId" not in body:
        return jsonify({"error": "productId is required"}), 400

    try:
        quantity = int(body.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity must be an integer"}), 400
    if quantity < 1 or quantity > 1000:
        return jsonify({"error": "Quantity must be between 1 and 1000"}), 400

    result = cart_service.add_item(SESSION_ID, body["productId"], quantity)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 201


@cart_bp.route("/items/<product_id>", methods=["PUT"])
def update_item(product_id):
    body = request.get_json()
    if not body or "quantity" not in body:
        return jsonify({"error": "quantity is required"}), 400

    try:
        quantity = int(body["quantity"])
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity must be an integer"}), 400
    if quantity < 0 or quantity > 1000:
        return jsonify({"error": "Quantity must be between 0 and 1000"}), 400

    if quantity == 0:
        result = cart_service.remove_item(SESSION_ID, product_id)
    else:
        result = cart_service.update_quantity(SESSION_ID, product_id, quantity)

    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@cart_bp.route("/items/<product_id>", methods=["DELETE"])
def remove_item(product_id):
    result = cart_service.remove_item(SESSION_ID, product_id)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@cart_bp.route("", methods=["DELETE"])
def clear_cart():
    cart_service.clear_cart(SESSION_ID)
    return jsonify({"message": "Cart cleared"})
