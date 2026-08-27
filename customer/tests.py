"""
Customer bulk import tests.
Tests: duplicate row in CSV → skip (not in row_errors); response has no error_summary or total_records.
"""

import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from customer.customer_views import CustomerViewSet
from customer.models import Customer

User = get_user_model()

# Minimal valid customer CSV (required: Customer Name, Person Name, Phone Number, Business Type)
MINIMAL_CSV_HEADER = "Customer Name,Person Name,Phone Number,Business Type\n"
MINIMAL_CSV_ONE_ROW = (
    MINIMAL_CSV_HEADER + "Unique Customer A,John Doe,9876543210,INDIAN\n"
)
# Two identical rows: first inserts, second is duplicate-in-CSV → skip, not in row_errors
MINIMAL_CSV_DUPLICATE_ROWS = MINIMAL_CSV_HEADER + (
    "Duplicate Row Customer,Jane Smith,9876543211,INDIAN\n"
    "Duplicate Row Customer,Jane Smith,9876543211,INDIAN\n"
)


class CustomerBulkImportResponseTest(TestCase):
    """Test that import response does not contain error_summary or total_records."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="import_test_user",
            email="importtest@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_response_does_not_contain_error_summary_or_total_records(self):
        """Formatted import response must not include error_summary or total_records."""
        view = CustomerViewSet()
        view.request = type("Req", (), {"user": self.user})()
        view.format_kwarg = None

        # Build a result dict as returned by BaseImporter.import_data()
        result = {
            "success": True,
            "message": "Import completed",
            "total_rows": 5,
            "total_records": 4,  # valid count - must not appear in response
            "inserted": 2,
            "updated": 1,
            "skipped": 1,
            "success_count": 3,
            "error_count": 0,
            "import_log_id": None,
            "dry_run": False,
        }
        response = view._format_import_response(result, is_success=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data") or {}
        self.assertNotIn(
            "error_summary", data, "response data must not contain error_summary"
        )
        self.assertNotIn(
            "total_records", data, "response data must not contain total_records"
        )


class CustomerBulkImportDuplicateRowTest(TestCase):
    """Test that duplicate row in CSV is skipped and does not appear in row_errors."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="dup_test_user",
            email="duptest@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_duplicate_row_in_csv_skipped_not_in_row_errors(self):
        """When CSV has two identical rows: first inserts, second is skipped and not in row_errors."""
        url = "/api/v1/customer/bulk-import/"
        csv_content = MINIMAL_CSV_DUPLICATE_ROWS.encode("utf-8")
        file = SimpleUploadedFile("customers.csv", csv_content, content_type="text/csv")
        response = self.client.post(url, {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data.get("data") or {}
        # First row inserts, second row is duplicate-in-CSV → skipped (not an error)
        self.assertGreaterEqual(
            data.get("inserted", 0), 1, "At least one row should be inserted"
        )
        self.assertGreaterEqual(
            data.get("skipped", 0), 1, "Duplicate row should be skipped"
        )
        # Duplicate row must not appear in row_errors (whole row same → skip, don't show in row_errors)
        row_errors = data.get("row_errors") or []
        row_numbers_in_errors = [e["row_number"] for e in row_errors]
        # Row 3 is the duplicate; it should not be in row_errors
        self.assertNotIn(
            3, row_numbers_in_errors, "Duplicate row (row 3) must not be in row_errors"
        )
        # Response must not contain error_summary or total_records
        self.assertNotIn("error_summary", data)
        self.assertNotIn("total_records", data)
