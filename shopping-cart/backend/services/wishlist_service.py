from models.cart import CartModel
from services.product_service import ProductService
from services.cart_service import CartService


class WishlistService:

    def __init__(self):
        self.model = CartModel()
        self.product_service = ProductService()
        self.cart_service = CartService()

    def get_wishlist(self, session_id):
        return self.model.get_wishlist_items(session_id)

    def add_item(self, session_id, product_id):
        product = self.product_service.get_by_id(product_id)
        if not product:
            return {"error": "Product not found"}

        item = {
            "sessionId": session_id,
            "productId": product_id,
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "listType": "wishlist",
        }
        self.model.put_item(item)
        return {"message": f"Saved {product['name']} to wishlist", "item": item}

    def remove_item(self, session_id, product_id):
        existing = self.model.get_item(session_id, product_id)
        if not existing:
            return {"error": "Item not in wishlist"}

        self.model.delete_item(session_id, product_id)
        return {"message": f"Removed {existing['name']} from wishlist"}

    def move_to_cart(self, session_id, product_id, keep_in_wishlist):
        existing = self.model.get_item(session_id, product_id)
        if not existing:
            return {"error": "Item not in wishlist"}

        result = self.cart_service.add_item(session_id, product_id, quantity=1)
        if "error" in result:
            return result

        if not keep_in_wishlist:
            self.model.delete_item(session_id, product_id)

        return {"message": "Moved to cart", "keepInWishlist": keep_in_wishlist}
