"""
TDD tests for DiscountService.
All DynamoDB calls are replaced with a fake in-memory store so tests
run without AWS credentials.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

from services.discount_service import DiscountService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future():
    return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

def _past():
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

def _make_service(discounts: dict):
    """Build a DiscountService backed by a fake in-memory model."""
    fake_model = MagicMock()
    fake_model.get.side_effect = lambda code: discounts.get(code.upper())
    svc = DiscountService.__new__(DiscountService)
    svc.model = fake_model
    return svc


# ---------------------------------------------------------------------------
# validate() — existence
# ---------------------------------------------------------------------------

class TestValidateExists:
    def test_returns_none_for_unknown_code(self):
        svc = _make_service({})
        assert svc.validate("NOPE", subtotal=100.0) is None

    def test_returns_discount_for_valid_percent_code(self):
        svc = _make_service({"SAVE10": {"code": "SAVE10", "type": "percent", "value": 10, "usedCount": 0}})
        result = svc.validate("SAVE10", subtotal=100.0)
        assert result is not None
        assert result["code"] == "SAVE10"

    def test_code_lookup_is_case_insensitive(self):
        svc = _make_service({"SAVE10": {"code": "SAVE10", "type": "percent", "value": 10, "usedCount": 0}})
        assert svc.validate("save10", subtotal=50.0) is not None


# ---------------------------------------------------------------------------
# validate() — expiry
# ---------------------------------------------------------------------------

class TestValidateExpiry:
    def test_expired_code_returns_none(self):
        svc = _make_service({"OLD": {"code": "OLD", "type": "fixed", "value": 5,
                                     "expiresAt": _past(), "usedCount": 0}})
        assert svc.validate("OLD", subtotal=50.0) is None

    def test_non_expired_code_is_valid(self):
        svc = _make_service({"FRESH": {"code": "FRESH", "type": "fixed", "value": 5,
                                       "expiresAt": _future(), "usedCount": 0}})
        assert svc.validate("FRESH", subtotal=50.0) is not None

    def test_code_without_expiry_is_valid(self):
        svc = _make_service({"FOREVER": {"code": "FOREVER", "type": "fixed", "value": 5, "usedCount": 0}})
        assert svc.validate("FOREVER", subtotal=50.0) is not None


# ---------------------------------------------------------------------------
# validate() — max uses
# ---------------------------------------------------------------------------

class TestValidateMaxUses:
    def test_exhausted_code_returns_none(self):
        svc = _make_service({"USED": {"code": "USED", "type": "fixed", "value": 5,
                                      "maxUses": 10, "usedCount": 10}})
        assert svc.validate("USED", subtotal=50.0) is None

    def test_code_with_uses_remaining_is_valid(self):
        svc = _make_service({"SOME": {"code": "SOME", "type": "fixed", "value": 5,
                                      "maxUses": 10, "usedCount": 5}})
        assert svc.validate("SOME", subtotal=50.0) is not None

    def test_zero_max_uses_means_unlimited(self):
        svc = _make_service({"INF": {"code": "INF", "type": "fixed", "value": 5,
                                     "maxUses": 0, "usedCount": 9999}})
        assert svc.validate("INF", subtotal=50.0) is not None


# ---------------------------------------------------------------------------
# calculate_discount() — percent
# ---------------------------------------------------------------------------

class TestCalculatePercent:
    def test_10_percent_off_100(self):
        svc = _make_service({})
        amount = svc.calculate_discount({"type": "percent", "value": 10}, subtotal=100.0)
        assert amount == pytest.approx(10.0)

    def test_percent_rounds_to_two_decimal_places(self):
        svc = _make_service({})
        amount = svc.calculate_discount({"type": "percent", "value": 10}, subtotal=33.33)
        assert amount == pytest.approx(3.33, abs=0.005)

    def test_100_percent_discount_equals_subtotal(self):
        svc = _make_service({})
        amount = svc.calculate_discount({"type": "percent", "value": 100}, subtotal=50.0)
        assert amount == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# calculate_discount() — fixed
# ---------------------------------------------------------------------------

class TestCalculateFixed:
    def test_fixed_5_off_100(self):
        svc = _make_service({})
        amount = svc.calculate_discount({"type": "fixed", "value": 5}, subtotal=100.0)
        assert amount == pytest.approx(5.0)

    def test_fixed_discount_capped_at_subtotal(self):
        svc = _make_service({})
        amount = svc.calculate_discount({"type": "fixed", "value": 999}, subtotal=20.0)
        assert amount == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# apply_to_cart() — full cart totals
# ---------------------------------------------------------------------------

class TestApplyToCart:
    BASE_CART = {
        "items": [],
        "itemCount": 1,
        "subtotal": 100.0,
        "tax": 8.0,
        "total": 108.0,
    }

    def test_percent_discount_recalculates_all_totals(self):
        svc = _make_service({})
        discount = {"type": "percent", "value": 10, "discountAmount": 10.0, "code": "SAVE10"}
        result = svc.apply_to_cart(dict(self.BASE_CART), discount)
        assert result["discountAmount"] == pytest.approx(10.0)
        assert result["subtotal"] == pytest.approx(100.0)       # original unchanged
        assert result["discountedSubtotal"] == pytest.approx(90.0)
        assert result["tax"] == pytest.approx(7.2)              # 90 × 0.08
        assert result["total"] == pytest.approx(97.2)           # 90 + 7.2

    def test_fixed_discount_recalculates_all_totals(self):
        svc = _make_service({})
        discount = {"type": "fixed", "value": 20, "discountAmount": 20.0, "code": "FLAT20"}
        result = svc.apply_to_cart(dict(self.BASE_CART), discount)
        assert result["discountedSubtotal"] == pytest.approx(80.0)
        assert result["tax"] == pytest.approx(6.4)
        assert result["total"] == pytest.approx(86.4)

    def test_discount_larger_than_subtotal_floors_at_zero(self):
        svc = _make_service({})
        discount = {"type": "fixed", "value": 999, "discountAmount": 100.0, "code": "BIG"}
        result = svc.apply_to_cart(dict(self.BASE_CART), discount)
        assert result["discountedSubtotal"] == pytest.approx(0.0)
        assert result["tax"] == pytest.approx(0.0)
        assert result["total"] == pytest.approx(0.0)

    def test_no_discount_returns_cart_unchanged(self):
        svc = _make_service({})
        result = svc.apply_to_cart(dict(self.BASE_CART), None)
        assert result["total"] == pytest.approx(108.0)
        assert "discountAmount" not in result
