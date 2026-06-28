from flask import Flask, jsonify
from flask_cors import CORS
from routes.products import products_bp
from routes.cart import cart_bp
from routes.orders import orders_bp
from routes.discounts import discounts_bp
from routes.wishlist import wishlist_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(products_bp, url_prefix="/api/products")
app.register_blueprint(cart_bp, url_prefix="/api/cart")
app.register_blueprint(orders_bp, url_prefix="/api/orders")
app.register_blueprint(discounts_bp, url_prefix="/api/discounts")
app.register_blueprint(wishlist_bp, url_prefix="/api/wishlist")


@app.route("/api/health")
def health_check():
    return {"status": "healthy", "service": "shopping-cart-api"}


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.error("Unhandled error: %s", error, exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    app.run(debug=False, port=5000)
