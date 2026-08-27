"""
Unit tests for Scrap Sale module.
"""

from decimal import Decimal
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase

from scrap_sale.models import ScrapSale
from scrap_sale.services.scrap_sale_service import (
    cancel_scrap_sale,
    get_available_scrap_items_for_sale,
    _get_available_qty,
)


class ScrapSaleModelTest(TestCase):
    """Model and status lifecycle tests."""

    def test_scrap_sale_status_choices(self):
        self.assertEqual(ScrapSale.STATUS_DRAFT, "DRAFT")
        self.assertEqual(ScrapSale.STATUS_FINALIZED, "FINALIZED")
        self.assertEqual(ScrapSale.STATUS_CANCELLED, "CANCELLED")


class ScrapSaleServiceTest(TestCase):
    """Service layer validation."""

    def test_get_available_qty_no_stock(self):
        from uuid import uuid4

        qty = _get_available_qty(uuid4())
        self.assertEqual(qty, Decimal("0"))

    def test_cancel_finalized_rejected(self):
        sale = MagicMock()
        sale.status = ScrapSale.STATUS_FINALIZED
        sale.refresh_from_db = MagicMock()
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            cancel_scrap_sale(sale, user)
        self.assertIn("FINALIZED", str(ctx.exception))

    def test_available_for_sale_returns_list(self):
        data = get_available_scrap_items_for_sale()
        self.assertIsInstance(data, list)
