import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class GatePass(models.Model):
    TYPE_RETURNABLE = "RETURNABLE"
    TYPE_NON_RETURNABLE = "NON_RETURNABLE"

    TYPE_CHOICES = [
        (TYPE_RETURNABLE, "Returnable"),
        (TYPE_NON_RETURNABLE, "Non Returnable"),
    ]

    STATUS_DRAFT = "DRAFT"
    STATUS_PENDING = "PENDING"
    STATUS_IN_PROCESS = "IN_PROCESS"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROCESS, "In Process"),
        (STATUS_CLOSED, "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gate_pass_no = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )
    date = models.DateField(db_index=True)
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
    )
    po_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional Purchase Order ID (UUID). Stored as raw UUID to avoid hard coupling to procurement app.",
    )
    party_name = models.CharField(max_length=255, db_index=True)
    vehicle_no = models.CharField(max_length=50, db_index=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="gate_passes_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_passes_updated",
    )
    deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_passes_deleted",
    )

    class Meta:
        db_table = "gate_pass"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["gate_pass_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["date"]),
            models.Index(fields=["type"]),
            models.Index(fields=["po_id"]),
            models.Index(fields=["party_name"]),
            models.Index(fields=["vehicle_no"]),
            models.Index(fields=["deleted", "is_archived"]),
        ]

    def __str__(self) -> str:
        return self.gate_pass_no

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class GatePassItem(models.Model):
    """Line items for Gate Pass. Audit: created_at for traceability."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gate_pass = models.ForeignKey(
        GatePass,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    description = models.TextField()
    unit = models.CharField(max_length=50)
    qty = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    purpose = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "gate_pass_item"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.gate_pass_id} - {self.description[:50]}"
