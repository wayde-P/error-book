"""
TDD tests for POST /api/discounts/validate.
boto3 is patched at import time so tests run without AWS credentials.
"""
import sys, os
# Patch env vars and boto3 before any app import
os.environ.setdefault("PRODUCTS_TABLE", "test-products")
os.environ.setdefault("CART_TABLE", "test-cart")
os.environ.setdefault("ORDERS_TABLE", "test-orders")
os.environ.setdefault("DISCOUNTS_TABLE", "test-discounts")

from unittest.mock import patch, MagicMock

# Stub out boto3.resource so DynamoDB clients never actually connect
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


class TestValidateEndpoint:
    def test_missing_code_returns_400(self, client):
        resp = client.post("/api/discounts/validate", json={})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_invalid_code_returns_404(self, client):
        with patch("routes.discounts.discount_service") as mock_svc:
            mock_svc.validate.return_value = None
            resp = client.post("/api/discounts/validate", json={"code": "NOPE"})
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Invalid or expired discount code"

    def test_valid_code_returns_200_with_discount_details(self, client):
        fake = {"code": "SAVE10", "type": "percent", "value": 10, "discountAmount": 5.0}
        with patch("routes.discounts.discount_service") as mock_svc:
            mock_svc.validate.return_value = fake
            resp = client.post("/api/discounts/validate",
                               json={"code": "SAVE10", "subtotal": 50.0})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == "SAVE10"
        assert data["discountAmount"] == 5.0

    def test_subtotal_defaults_to_zero_when_omitted(self, client):
        fake = {"code": "X", "type": "fixed", "value": 5, "discountAmount": 0.0}
        with patch("routes.discounts.discount_service") as mock_svc:
            mock_svc.validate.return_value = fake
            resp = client.post("/api/discounts/validate", json={"code": "X"})
        assert resp.status_code == 200
        mock_svc.validate.assert_called_once_with("X", 0.0)
