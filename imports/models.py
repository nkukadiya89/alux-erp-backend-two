"""
Import Log and Error Tracking Models
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ImportLog(models.Model):
    """
    Tracks bulk import operations
    """

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("partial", "Partial Success"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module_name = models.CharField(
        max_length=100, db_index=True
    )  # e.g., "Plant", "Customer"
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # "excel" or "csv"
    total_rows = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_summary = models.JSONField(default=dict, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="import_logs_created",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "import_log"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["module_name", "status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self):
        return f"{self.module_name} Import - {self.file_name} ({self.status})"

    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_rows == 0:
            return 0
        return round((self.success_count / self.total_rows) * 100, 2)

    def mark_completed(self, success_count, error_count):
        """Mark import as completed"""
        self.status = "completed" if error_count == 0 else "partial"
        self.success_count = success_count
        self.error_count = error_count
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, error_message=None):
        """Mark import as failed"""
        self.status = "failed"
        self.completed_at = timezone.now()
        if error_message:
            self.error_summary = {"error": str(error_message)}
        self.save()


class ImportErrorRow(models.Model):
    """
    Tracks individual row errors during import
    """

    ERROR_TYPE_CHOICES = (
        ("validation", "Validation Error"),
        ("reference", "Reference Error"),
        ("business_rule", "Business Rule Violation"),
        ("duplicate", "Duplicate Entry"),
        ("database", "Database Error"),
        ("unknown", "Unknown Error"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_log = models.ForeignKey(
        ImportLog,
        on_delete=models.CASCADE,
        related_name="error_rows",
        db_index=True,
    )
    row_number = models.IntegerField(db_index=True)  # Excel/CSV row number (1-indexed)
    error_type = models.CharField(
        max_length=20, choices=ERROR_TYPE_CHOICES, default="validation"
    )
    field_name = models.CharField(max_length=100, null=True, blank=True)
    error_message = models.TextField()
    raw_data = models.JSONField(default=dict)  # Store original row data for reference
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_error_row"
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["import_log", "row_number"]),
            models.Index(fields=["error_type"]),
        ]

    def __str__(self):
        return f"Row {self.row_number}: {self.error_message}"
