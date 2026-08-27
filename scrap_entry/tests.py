"""
Unit tests for Scrap Entry module.
"""

from decimal import Decimal
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase

from scrap_entry.models import ScrapEntry
from scrap_entry.services.scrap_entry_service import (
    mark_scrap_transferred,
    post_scrap_entry,
    update_scrap_entry,
    archive_scrap_entries,
)


class ScrapEntryModelTest(TestCase):
    """Model and status lifecycle tests."""

    def test_scrap_entry_status_choices(self):
        self.assertEqual(ScrapEntry.STATUS_DRAFT, "DRAFT")
        self.assertEqual(ScrapEntry.STATUS_POSTED, "POSTED")
        self.assertEqual(ScrapEntry.STATUS_TRANSFERRED, "TRANSFERRED")


class ScrapEntryServiceTest(TestCase):
    """Service layer validation."""

    def test_post_non_draft_rejected(self):
        entry = MagicMock()
        entry.status = ScrapEntry.STATUS_POSTED
        entry.refresh_from_db = MagicMock()
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            post_scrap_entry(entry, user)
        self.assertIn("DRAFT", str(ctx.exception))

    def test_mark_transferred_non_posted_rejected(self):
        entry = MagicMock()
        entry.status = ScrapEntry.STATUS_DRAFT
        entry.refresh_from_db = MagicMock()
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            mark_scrap_transferred(entry, user)
        self.assertIn("POSTED", str(ctx.exception))

    def test_update_posted_rejected(self):
        entry = MagicMock()
        entry.status = ScrapEntry.STATUS_POSTED
        entry.updated_at = None
        entry.updated_by = None
        user = MagicMock()
        with self.assertRaises(ValidationError) as ctx:
            update_scrap_entry(entry, {"remarks": "x"}, user)
        self.assertIn("DRAFT", str(ctx.exception))

    def test_archive_empty_ids(self):
        user = MagicMock()
        updated = archive_scrap_entries([], user)
        self.assertEqual(updated, 0)
