import logging

from flask import Blueprint, jsonify, request
from services.product_service import ProductService

logger = logging.getLogger(__name__)

products_bp = Blueprint("products", __name__)
product_service = ProductService()


@products_bp.route("", methods=["GET"])
def list_products():
    """Return all products, optionally filtered by category."""
    try:
        category = request.args.get("category", "").strip() or None
        if category:
            products = product_service.get_by_category(category)
        else:
            products = product_service.get_all()
        return jsonify({"products": products, "count": len(products)})
    except Exception as exc:
        logger.error("GET /products error: %s", exc)
        return jsonify({"error": "Failed to retrieve products"}), 500


@products_bp.route("/<product_id>", methods=["GET"])
def get_product(product_id: str):
    """Return a single product by its ID."""
    if not product_id or not product_id.strip():
        return jsonify({"error": "product_id is required"}), 400
    try:
        product = product_service.get_by_id(product_id.strip())
        if not product:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(product)
    except Exception as exc:
        logger.error("GET /products/%s error: %s", product_id, exc)
        return jsonify({"error": "Failed to retrieve product"}), 500


@products_bp.route("/categories", methods=["GET"])
def list_categories():
    """Return the list of all available product categories."""
    try:
        categories = product_service.get_categories()
        return jsonify({"categories": categories})
    except Exception as exc:
        logger.error("GET /products/categories error: %s", exc)
        return jsonify({"error": "Failed to retrieve categories"}), 500


@products_bp.route("/search", methods=["GET"])
def search_products():
    """Search products by keyword; requires query param 'q'."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Search query 'q' is required"}), 400
    try:
        results = product_service.search(query)
        return jsonify({"products": results, "count": len(results)})
    except Exception as exc:
        logger.error("GET /products/search error: %s", exc)
        return jsonify({"error": "Search failed"}), 500
