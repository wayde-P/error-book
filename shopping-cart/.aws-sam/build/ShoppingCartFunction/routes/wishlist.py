from flask import Blueprint, jsonify, request
from services.wishlist_service import WishlistService

wishlist_bp = Blueprint("wishlist", __name__)
wishlist_service = WishlistService()

SESSION_ID = "workshop-user"


@wishlist_bp.route("", methods=["GET"])
def get_wishlist():
    items = wishlist_service.get_wishlist(SESSION_ID)
    return jsonify(items)


@wishlist_bp.route("/items", methods=["POST"])
def add_item():
    body = request.get_json()
    if not body or "productId" not in body:
        return jsonify({"error": "productId is required"}), 400

    result = wishlist_service.add_item(SESSION_ID, body["productId"])
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 201


@wishlist_bp.route("/items/<product_id>", methods=["DELETE"])
def remove_item(product_id):
    result = wishlist_service.remove_item(SESSION_ID, product_id)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@wishlist_bp.route("/items/<product_id>/move-to-cart", methods=["POST"])
def move_to_cart(product_id):
    body = request.get_json() or {}
    keep = body.get("keepInWishlist", False)
    result = wishlist_service.move_to_cart(SESSION_ID, product_id, keep_in_wishlist=keep)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)
