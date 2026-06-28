"""
TDD tests for CartService.get_cart() with discount support.
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


def _make_cart_service(items):
    with patch("boto3.resource"):
        svc = CartService()
    svc.model = MagicMock()
    svc.model.get_items.return_value = items
    return svc


class TestGetCartWithDiscount:
    ITEMS = [{"productId": "p1", "name": "X", "price": 50.0, "quantity": 2, "image": ""}]

    def test_get_cart_without_discount_returns_standard_totals(self):
        svc = _make_cart_service(self.ITEMS)
        cart = svc.get_cart("sess", discount=None)
        assert cart["subtotal"] == pytest.approx(100.0)
        assert cart["tax"] == pytest.approx(8.0)
        assert cart["total"] == pytest.approx(108.0)
        assert "discountAmount" not in cart

    def test_get_cart_with_percent_discount_applies_to_totals(self):
        svc = _make_cart_service(self.ITEMS)
        discount = {"code": "SAVE10", "type": "percent", "value": 10, "discountAmount": 10.0}
        cart = svc.get_cart("sess", discount=discount)
        assert cart["discountAmount"] == pytest.approx(10.0)
        assert cart["discountedSubtotal"] == pytest.approx(90.0)
        assert cart["tax"] == pytest.approx(7.2)
        assert cart["total"] == pytest.approx(97.2)

    def test_get_cart_with_fixed_discount_applies_to_totals(self):
        svc = _make_cart_service(self.ITEMS)
        discount = {"code": "FLAT20", "type": "fixed", "value": 20, "discountAmount": 20.0}
        cart = svc.get_cart("sess", discount=discount)
        assert cart["discountedSubtotal"] == pytest.approx(80.0)
        assert cart["total"] == pytest.approx(86.4)
