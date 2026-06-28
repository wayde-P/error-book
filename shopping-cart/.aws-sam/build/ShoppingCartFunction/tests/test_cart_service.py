"""
pytest tests for CartService — add, remove, and total calculations.
DynamoDB and ProductService are replaced with in-memory fakes.
"""
import sys, os
os.environ.setdefault("PRODUCTS_TABLE", "test-products")
os.environ.setdefault("CART_TABLE", "test-cart")
os.environ.setdefault("ORDERS_TABLE", "test-orders")
os.environ.setdefault("DISCOUNTS_TABLE", "test-discounts")

from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.cart_service import CartService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRODUCT_A = {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "category": "Tools"}
PRODUCT_B = {"productId": "b2", "name": "Gadget", "price": 25.0, "image": "⚙️", "category": "Tools"}


def _make_service(cart_items=None, products=None):
    """Build a CartService backed by in-memory fakes."""
    cart_store = {item["productId"]: item for item in (cart_items or [])}
    product_catalog = {p["productId"]: p for p in (products or [PRODUCT_A, PRODUCT_B])}

    with patch("boto3.resource"):
        svc = CartService()

    # Fake CartModel
    fake_model = MagicMock()
    fake_model.get_items.side_effect = lambda sid: list(cart_store.values())
    fake_model.get_item.side_effect = lambda sid, pid: cart_store.get(pid)
    fake_model.put_item.side_effect = lambda item: cart_store.update({item["productId"]: item})
    fake_model.delete_item.side_effect = lambda sid, pid: cart_store.pop(pid, None)
    fake_model.clear.side_effect = lambda sid: cart_store.clear()
    svc.model = fake_model

    # Fake ProductService
    fake_products = MagicMock()
    fake_products.get_by_id.side_effect = lambda pid: product_catalog.get(pid)
    svc.product_service = fake_products

    # Fake DiscountService (no-op)
    fake_discounts = MagicMock()
    fake_discounts.apply_to_cart.side_effect = lambda cart, discount: cart
    svc.discount_service = fake_discounts

    return svc, cart_store


SESSION = "test-session"


# ---------------------------------------------------------------------------
# Adding items
# ---------------------------------------------------------------------------

class TestAddItem:
    def test_adds_new_item_to_empty_cart(self):
        svc, store = _make_service()
        result = svc.add_item(SESSION, "a1", quantity=1)
        assert "error" not in result
        assert store["a1"]["quantity"] == 1
        assert store["a1"]["name"] == "Widget"

    def test_snapshots_product_name_price_image_at_add_time(self):
        svc, store = _make_service()
        svc.add_item(SESSION, "a1", quantity=1)
        item = store["a1"]
        assert item["name"] == PRODUCT_A["name"]
        assert item["price"] == PRODUCT_A["price"]
        assert item["image"] == PRODUCT_A["image"]

    def test_adding_same_product_twice_accumulates_quantity(self):
        svc, store = _make_service()
        svc.add_item(SESSION, "a1", quantity=2)
        svc.add_item(SESSION, "a1", quantity=3)
        assert store["a1"]["quantity"] == 5

    def test_adding_multiple_quantity_at_once(self):
        svc, store = _make_service()
        svc.add_item(SESSION, "b2", quantity=4)
        assert store["b2"]["quantity"] == 4

    def test_returns_error_for_unknown_product(self):
        svc, store = _make_service()
        result = svc.add_item(SESSION, "NOPE", quantity=1)
        assert result == {"error": "Product not found"}
        assert len(store) == 0

    def test_add_two_different_products_stored_independently(self):
        svc, store = _make_service()
        svc.add_item(SESSION, "a1", quantity=1)
        svc.add_item(SESSION, "b2", quantity=2)
        assert len(store) == 2
        assert store["a1"]["quantity"] == 1
        assert store["b2"]["quantity"] == 2


# ---------------------------------------------------------------------------
# Removing items
# ---------------------------------------------------------------------------

class TestRemoveItem:
    def test_removes_existing_item(self):
        svc, store = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 2}
        ])
        result = svc.remove_item(SESSION, "a1")
        assert "error" not in result
        assert "a1" not in store

    def test_returns_error_when_removing_item_not_in_cart(self):
        svc, store = _make_service()
        result = svc.remove_item(SESSION, "a1")
        assert result == {"error": "Item not in cart"}

    def test_remove_one_item_leaves_others_intact(self):
        svc, store = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 1},
            {"productId": "b2", "name": "Gadget", "price": 25.0, "image": "⚙️", "quantity": 3},
        ])
        svc.remove_item(SESSION, "a1")
        assert "a1" not in store
        assert store["b2"]["quantity"] == 3

    def test_clear_cart_removes_all_items(self):
        svc, store = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 1},
            {"productId": "b2", "name": "Gadget", "price": 25.0, "image": "⚙️", "quantity": 2},
        ])
        svc.clear_cart(SESSION)
        assert len(store) == 0


# ---------------------------------------------------------------------------
# Updating quantity
# ---------------------------------------------------------------------------

class TestUpdateQuantity:
    def test_updates_quantity_of_existing_item(self):
        svc, store = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 1}
        ])
        result = svc.update_quantity(SESSION, "a1", 5)
        assert "error" not in result
        assert store["a1"]["quantity"] == 5

    def test_returns_error_when_updating_item_not_in_cart(self):
        svc, store = _make_service()
        result = svc.update_quantity(SESSION, "a1", 3)
        assert result == {"error": "Item not in cart"}


# ---------------------------------------------------------------------------
# Calculating totals
# ---------------------------------------------------------------------------

class TestGetCart:
    def test_empty_cart_has_zero_totals(self):
        svc, _ = _make_service()
        cart = svc.get_cart(SESSION)
        assert cart["subtotal"] == 0.0
        assert cart["tax"] == 0.0
        assert cart["total"] == 0.0
        assert cart["itemCount"] == 0

    def test_single_item_subtotal(self):
        svc, _ = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 3}
        ])
        cart = svc.get_cart(SESSION)
        assert cart["subtotal"] == pytest.approx(30.0)

    def test_multiple_items_subtotal(self):
        svc, _ = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 2},
            {"productId": "b2", "name": "Gadget", "price": 25.0, "image": "⚙️", "quantity": 1},
        ])
        cart = svc.get_cart(SESSION)
        assert cart["subtotal"] == pytest.approx(45.0)   # 2×10 + 1×25

    def test_tax_is_8_percent_of_subtotal(self):
        svc, _ = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 1}
        ])
        cart = svc.get_cart(SESSION)
        assert cart["tax"] == pytest.approx(0.80)

    def test_total_equals_subtotal_plus_tax(self):
        svc, _ = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 1}
        ])
        cart = svc.get_cart(SESSION)
        assert cart["total"] == pytest.approx(10.80)

    def test_item_count_sums_all_quantities(self):
        svc, _ = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 3},
            {"productId": "b2", "name": "Gadget", "price": 25.0, "image": "⚙️", "quantity": 2},
        ])
        cart = svc.get_cart(SESSION)
        assert cart["itemCount"] == 5

    def test_cart_items_list_returned(self):
        svc, _ = _make_service(cart_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "quantity": 1}
        ])
        cart = svc.get_cart(SESSION)
        assert len(cart["items"]) == 1
        assert cart["items"][0]["productId"] == "a1"
