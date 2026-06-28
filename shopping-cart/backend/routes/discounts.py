from flask import Blueprint, jsonify, request
from services.discount_service import DiscountService
from services.cart_service import CartService

discounts_bp = Blueprint("discounts", __name__)
discount_service = DiscountService()
cart_service = CartService()

SESSION_ID = "workshop-user"


@discounts_bp.route("/validate", methods=["POST"])
def validate_discount():
    """Validate a discount code and return discount amount against the current cart subtotal."""
    body = request.get_json() or {}
    code = body.get("code")
    if not code:
        return jsonify({"error": "code is required"}), 400
    if not isinstance(code, str):
        return jsonify({"error": "code must be a string"}), 400

    try:
        # Always calculate subtotal server-side — never trust client-provided value.
        cart = cart_service.get_cart(SESSION_ID)
        subtotal = cart["subtotal"]

        result = discount_service.validate(code, subtotal)
        if not result:
            return jsonify({"error": "Invalid or expired discount code"}), 404

        return jsonify(result), 200
    except Exception as exc:
        import logging
        logging.error("POST /discounts/validate error: %s", exc)
        return jsonify({"error": "An unexpected error occurred"}), 500
