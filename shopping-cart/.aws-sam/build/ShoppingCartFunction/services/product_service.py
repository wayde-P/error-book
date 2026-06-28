from models.product import ProductModel


class ProductService:

    def __init__(self):
        """Initialize ProductService with the product model."""
        self.model = ProductModel()

    def get_all(self):
        """Return all products, auto-seeding demo data on first access if the table is empty."""
        products = self.model.scan_all()
        if not products:
            # Auto-seed demo products on first access so the app works
            # immediately after deployment without a separate data-load step.
            self._seed_products()
            products = self.model.scan_all()
        return products

    def get_by_id(self, product_id):
        """Return a single product by product_id, or None if not found."""
        return self.model.get(product_id)

    def get_by_category(self, category):
        """Return all products matching the given category (case-insensitive)."""
        allProducts = self.get_all()
        return [p for p in allProducts if p.get("category", "").lower() == category.lower()]

    def get_categories(self):
        """Return a sorted list of all unique product categories."""
        products = self.get_all()
        categories = list(set(p.get("category", "Uncategorized") for p in products))
        categories.sort()
        return categories

    def search(self, query):
        """Return all products whose name contains query (case-insensitive)."""
        allProducts = self.get_all()
        queryLower = query.lower()
        return [p for p in allProducts if queryLower in p.get("name", "").lower()]

    def _seed_products(self):
        """Insert default demo products into the table."""
        defaultProducts = [
            {"productId": "1", "name": "Wireless Headphones", "price": "49.99", "category": "Electronics", "image": "🎧", "description": "Premium wireless headphones with noise cancellation."},
            {"productId": "2", "name": "USB-C Cable", "price": "12.99", "category": "Electronics", "image": "🔌", "description": "Fast-charging USB-C cable, 2m braided nylon."},
            {"productId": "3", "name": "Laptop Stand", "price": "34.99", "category": "Accessories", "image": "💻", "description": "Ergonomic aluminum laptop stand with adjustable height."},
            {"productId": "4", "name": "Mechanical Keyboard", "price": "79.99", "category": "Electronics", "image": "⌨️", "description": "RGB mechanical keyboard with Cherry MX switches."},
            {"productId": "5", "name": "Mouse Pad XL", "price": "9.99", "category": "Accessories", "image": "🖱️", "description": "Extended mouse pad with stitched edges, 900x400mm."},
            {"productId": "6", "name": "Webcam HD", "price": "59.99", "category": "Electronics", "image": "📷", "description": "1080p webcam with built-in microphone and auto-focus."},
            {"productId": "7", "name": "Coffee Mug", "price": "14.99", "category": "Office", "image": "☕", "description": "Insulated stainless steel mug, keeps drinks hot for 6 hours."},
            {"productId": "8", "name": "Desk Lamp", "price": "29.99", "category": "Office", "image": "💡", "description": "LED desk lamp with 5 brightness levels and USB charging port."},
            {"productId": "9", "name": "Notebook Pack", "price": "7.99", "category": "Office", "image": "📓", "description": "3-pack dotted grid notebooks, A5 size, 120 pages each."},
            {"productId": "10", "name": "Backpack", "price": "44.99", "category": "Accessories", "image": "🎒", "description": "Water-resistant laptop backpack with USB charging port."},
        ]
        for product in defaultProducts:
            self.model.put(product)
