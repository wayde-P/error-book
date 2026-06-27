from flask import Blueprint, jsonify, request
from services.discount_service import DiscountService

discounts_bp = Blueprint("discounts", __name__)
discount_service = DiscountService()


@discounts_bp.route("/validate", methods=["POST"])
def validate_discount():
    body = request.get_json() or {}
    code = body.get("code")
    if not code:
        return jsonify({"error": "code is required"}), 400

    subtotal = float(body.get("subtotal", 0.0))
    result = discount_service.validate(code, subtotal)
    if not result:
        return jsonify({"error": "Invalid or expired discount code"}), 404

    return jsonify(result), 200
