from flask import Blueprint, jsonify, request
from services.wishlist_service import WishlistService

wishlist_bp = Blueprint("wishlist", __name__)
wishlist_service = WishlistService()

SESSION_ID = "workshop-user"


@wishlist_bp.route("", methods=["GET"])
def get_wishlist():
    """Return all items in the current user's wishlist."""
    items = wishlist_service.get_wishlist(SESSION_ID)
    return jsonify(items)


@wishlist_bp.route("/items", methods=["POST"])
def add_item():
    """Add a product to the wishlist; requires a non-empty productId in the request body."""
    body = request.get_json()
    if not body or not body.get("productId"):
        return jsonify({"error": "productId is required"}), 400

    result = wishlist_service.add_item(SESSION_ID, body["productId"])
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 201


@wishlist_bp.route("/items/<product_id>", methods=["DELETE"])
def remove_item(product_id):
    """Remove a product from the wishlist by product_id path parameter."""
    result = wishlist_service.remove_item(SESSION_ID, product_id)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@wishlist_bp.route("/items/<product_id>/move-to-cart", methods=["POST"])
def move_to_cart(product_id):
    """Move a wishlist item to the cart; optional keepInWishlist boolean defaults to False."""
    body = request.get_json() or {}
    keep = body.get("keepInWishlist", False)
    if not isinstance(keep, bool):
        return jsonify({"error": "keepInWishlist must be a boolean"}), 400
    result = wishlist_service.move_to_cart(SESSION_ID, product_id, keep_in_wishlist=keep)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)
