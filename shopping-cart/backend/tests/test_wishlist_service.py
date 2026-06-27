import sys, os
os.environ.setdefault("PRODUCTS_TABLE", "test-products")
os.environ.setdefault("CART_TABLE", "test-cart")
os.environ.setdefault("ORDERS_TABLE", "test-orders")
os.environ.setdefault("DISCOUNTS_TABLE", "test-discounts")

from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.wishlist_service import WishlistService

PRODUCT_A = {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "category": "Tools"}

def _make_service(wishlist_items=None, products=None):
    wishlist_store = {item["productId"]: item for item in (wishlist_items or [])}
    product_catalog = {p["productId"]: p for p in (products or [PRODUCT_A])}

    with patch("boto3.resource"):
        svc = WishlistService()

    fake_model = MagicMock()
    fake_model.get_wishlist_items.side_effect = lambda sid: list(wishlist_store.values())
    fake_model.get_item.side_effect = lambda sid, pid: wishlist_store.get(pid)
    fake_model.put_item.side_effect = lambda item: wishlist_store.update({item["productId"]: item})
    fake_model.delete_item.side_effect = lambda sid, pid: wishlist_store.pop(pid, None)
    svc.model = fake_model

    fake_products = MagicMock()
    fake_products.get_by_id.side_effect = lambda pid: product_catalog.get(pid)
    svc.product_service = fake_products

    fake_cart_service = MagicMock()
    fake_cart_service.add_item.side_effect = lambda sid, pid, quantity=1: {"message": f"Added to cart", "item": {"productId": pid}}
    svc.cart_service = fake_cart_service

    return svc, wishlist_store

SESSION = "test-session"


class TestAddItem:
    def test_adds_product_to_wishlist_with_snapshot(self):
        svc, store = _make_service()
        result = svc.add_item(SESSION, "a1")
        assert "error" not in result
        assert store["a1"]["name"] == "Widget"
        assert store["a1"]["price"] == 10.0
        assert store["a1"]["image"] == "🔧"
        assert store["a1"]["listType"] == "wishlist"

    def test_returns_error_for_unknown_product(self):
        svc, store = _make_service()
        result = svc.add_item(SESSION, "NOPE")
        assert result == {"error": "Product not found"}
        assert len(store) == 0


class TestRemoveItem:
    def test_removes_existing_wishlist_item(self):
        svc, store = _make_service(wishlist_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "listType": "wishlist"}
        ])
        result = svc.remove_item(SESSION, "a1")
        assert "error" not in result
        assert "a1" not in store

    def test_returns_error_when_item_not_in_wishlist(self):
        svc, store = _make_service()
        result = svc.remove_item(SESSION, "a1")
        assert result == {"error": "Item not in wishlist"}


class TestMoveToCart:
    def test_move_to_cart_without_keep_removes_from_wishlist(self):
        svc, store = _make_service(wishlist_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "listType": "wishlist"}
        ])
        result = svc.move_to_cart(SESSION, "a1", keep_in_wishlist=False)
        assert "error" not in result
        assert "a1" not in store
        svc.cart_service.add_item.assert_called_once_with(SESSION, "a1", quantity=1)

    def test_move_to_cart_with_keep_leaves_wishlist_intact(self):
        svc, store = _make_service(wishlist_items=[
            {"productId": "a1", "name": "Widget", "price": 10.0, "image": "🔧", "listType": "wishlist"}
        ])
        result = svc.move_to_cart(SESSION, "a1", keep_in_wishlist=True)
        assert "error" not in result
        assert "a1" in store
        svc.cart_service.add_item.assert_called_once_with(SESSION, "a1", quantity=1)
