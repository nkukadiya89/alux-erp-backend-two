"""
Unit tests for Scrap Transfer module.
"""

from decimal import Decimal
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase

from scrap_transfer.models import ScrapTransfer
from scrap_transfer.services.scrap_transfer_service import (
    submit_scrap_transfer,
    complete_scrap_transfer,
    update_scrap_transfer,
    cancel_submit,
    archive_scrap_transfers,
)


class ScrapTransferModelTest(TestCase):
    """Model and status lifecycle tests."""

    def test_scrap_transfer_status_choices(self):
        self.assertEqual(ScrapTransfer.STATUS_DRAFT, "DRAFT")
        self.assertEqual(ScrapTransfer.STATUS_SUBMITTED, "SUBMITTED")
        self.assertEqual(ScrapTransfer.STATUS_COMPLETED, "COMPLETED")


class ScrapTransferServiceTest(TestCase):
    """Service layer validation."""

    def test_submit_non_draft_rejected(self):
        transfer = MagicMock()
        transfer.status = ScrapTransfer.STATUS_SUBMITTED
        transfer.refresh_from_db = MagicMock()
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            submit_scrap_transfer(transfer, user)
        self.assertIn("DRAFT", str(ctx.exception))

    def test_complete_non_submitted_rejected(self):
        transfer = MagicMock()
        transfer.status = ScrapTransfer.STATUS_DRAFT
        transfer.refresh_from_db = MagicMock()
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            complete_scrap_transfer(transfer, user)
        self.assertIn("SUBMITTED", str(ctx.exception))

    def test_update_submitted_rejected(self):
        transfer = MagicMock()
        transfer.status = ScrapTransfer.STATUS_SUBMITTED
        transfer.updated_at = None
        transfer.updated_by = None
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            update_scrap_transfer(transfer, {"remarks": "x"}, user)
        self.assertIn("DRAFT", str(ctx.exception))

    def test_cancel_submit_completed_rejected(self):
        transfer = MagicMock()
        transfer.status = ScrapTransfer.STATUS_COMPLETED
        transfer.refresh_from_db = MagicMock()
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            cancel_submit(transfer, user)
        self.assertIn("COMPLETED", str(ctx.exception))

    def test_archive_empty_ids(self):
        user = MagicMock()
        updated = archive_scrap_transfers([], user)
        self.assertEqual(updated, 0)
