"""
TDD tests for cart route input validation.
boto3 is patched at import time so tests run without AWS credentials.
"""
import sys, os
os.environ.setdefault("PRODUCTS_TABLE", "test-products")
os.environ.setdefault("CART_TABLE", "test-cart")
os.environ.setdefault("ORDERS_TABLE", "test-orders")
os.environ.setdefault("DISCOUNTS_TABLE", "test-discounts")

from unittest.mock import patch, MagicMock

_fake_table = MagicMock()
_fake_resource = MagicMock()
_fake_resource.Table.return_value = _fake_table

with patch("boto3.resource", return_value=_fake_resource):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import app as flask_app

import pytest


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


EMPTY_CART = {"items": [], "count": 0, "subtotal": 0.0, "tax": 0.0, "total": 0.0}


class TestAddItem:
    def test_missing_body_returns_400(self, client):
        resp = client.post("/api/cart/items", content_type="application/json")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_productId_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"quantity": 1})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "productId" in data["error"]

    def test_empty_productId_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"productId": "  "})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_non_string_productId_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"productId": 123})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_non_integer_quantity_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"productId": "p1", "quantity": "abc"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "integer" in data["error"].lower()

    def test_zero_quantity_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"productId": "p1", "quantity": 0})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_negative_quantity_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"productId": "p1", "quantity": -1})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_quantity_over_1000_returns_400(self, client):
        resp = client.post("/api/cart/items", json={"productId": "p1", "quantity": 1001})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_valid_item_calls_service(self, client):
        with patch("routes.cart.cart_service") as mock_svc:
            mock_svc.add_item.return_value = {"productId": "p1", "quantity": 2}
            resp = client.post("/api/cart/items", json={"productId": "p1", "quantity": 2})
        assert resp.status_code == 201
        mock_svc.add_item.assert_called_once_with("workshop-user", "p1", 2)

    def test_quantity_defaults_to_1(self, client):
        with patch("routes.cart.cart_service") as mock_svc:
            mock_svc.add_item.return_value = {"productId": "p1", "quantity": 1}
            resp = client.post("/api/cart/items", json={"productId": "p1"})
        assert resp.status_code == 201
        mock_svc.add_item.assert_called_once_with("workshop-user", "p1", 1)


class TestUpdateItem:
    def test_missing_body_returns_400(self, client):
        resp = client.put("/api/cart/items/p1", content_type="application/json")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_quantity_returns_400(self, client):
        resp = client.put("/api/cart/items/p1", json={"other": "field"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "quantity" in data["error"]

    def test_non_integer_quantity_returns_400(self, client):
        resp = client.put("/api/cart/items/p1", json={"quantity": "lots"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "integer" in data["error"].lower()

    def test_negative_quantity_returns_400(self, client):
        resp = client.put("/api/cart/items/p1", json={"quantity": -5})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_quantity_over_1000_returns_400(self, client):
        resp = client.put("/api/cart/items/p1", json={"quantity": 1001})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_zero_quantity_removes_item(self, client):
        with patch("routes.cart.cart_service") as mock_svc:
            mock_svc.remove_item.return_value = {"message": "removed"}
            resp = client.put("/api/cart/items/p1", json={"quantity": 0})
        assert resp.status_code == 200
        mock_svc.remove_item.assert_called_once_with("workshop-user", "p1")

    def test_valid_quantity_updates_item(self, client):
        with patch("routes.cart.cart_service") as mock_svc:
            mock_svc.update_quantity.return_value = {"productId": "p1", "quantity": 5}
            resp = client.put("/api/cart/items/p1", json={"quantity": 5})
        assert resp.status_code == 200
        mock_svc.update_quantity.assert_called_once_with("workshop-user", "p1", 5)


class TestGetCart:
    def test_no_code_returns_cart(self, client):
        with patch("routes.cart.cart_service") as mock_svc:
            mock_svc.get_cart.return_value = EMPTY_CART
            resp = client.get("/api/cart")
        assert resp.status_code == 200

    def test_whitespace_only_code_returns_400(self, client):
        resp = client.get("/api/cart?code=   ")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_valid_code_applies_discount(self, client):
        fake_discount = {"code": "SAVE10", "type": "percent", "value": 10, "discountAmount": 2.0}
        with patch("routes.cart.cart_service") as mock_svc, \
             patch("routes.cart.discount_service") as mock_disc:
            mock_svc.get_cart.return_value = {**EMPTY_CART, "subtotal": 20.0}
            mock_disc.validate.return_value = fake_discount
            resp = client.get("/api/cart?code=SAVE10")
        assert resp.status_code == 200
