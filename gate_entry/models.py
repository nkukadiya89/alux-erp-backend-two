from decimal import Decimal
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from settings.models import BaseModule
from transporter.models import Transporter
from vendor.models import Vendor


class GateEntry(BaseModule):
    """Gate entry for vehicle/driver inward and outward at gate."""

    STATUS_IN_COMPANY = "in_company"
    STATUS_CLOSE = "close"

    STATUS_CHOICES = [
        (STATUS_IN_COMPANY, "In Company"),
        (STATUS_CLOSE, "Close"),
    ]

    gate_entry_no = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        editable=False,
    )
    date = models.DateField(db_index=True)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="gate_entries",
        db_index=True,
    )
    driver_name = models.CharField(max_length=255, db_index=True)
    transporter = models.ForeignKey(
        Transporter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_entries",
        db_index=True,
    )
    driver_mobile_no = models.CharField(max_length=20, blank=True, null=True)
    vehicle_no = models.CharField(max_length=50, db_index=True)
    challan_no = models.CharField(max_length=100, blank=True, null=True)
    invoice_no = models.CharField(max_length=100, blank=True, null=True)
    inward_time = models.TimeField()
    outward_time = models.TimeField(blank=True, null=True)
    empty_vehicle_weight = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Required before closing gate entry.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_COMPANY,
        db_index=True,
    )
    is_archived = models.BooleanField(default=False, db_index=True)


    class Meta:
        db_table = "gate_entry"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["gate_entry_no"]),
            models.Index(fields=["date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vendor_id"]),
            models.Index(fields=["transporter_id"]),
            models.Index(fields=["vehicle_no"]),
            models.Index(fields=["deleted", "-created_at"]),
            models.Index(fields=["deleted", "is_archived"]),
        ]
        verbose_name = "Gate Entry"
        verbose_name_plural = "Gate Entries"

    def __str__(self):
        return self.gate_entry_no

    # def save(self, *args, **kwargs):
    #     if not self._state.adding:
    #         self.updated_at = timezone.now()
    #     super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
            if not self.gate_entry_no:
                from utils.generate_number import generate_gate_entry_no
                self.gate_entry_no = generate_gate_entry_no()

            if not self._state.adding:
                self.updated_at = timezone.now()
                
            super().save(*args, **kwargs)
class GateEntryItem(models.Model):
    """
    Line items for Gate Entry. Audit: created_at for traceability.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gate_entry = models.ForeignKey(
        GateEntry,
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
        db_table = "gate_entry_item"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.gate_entry_id} - {self.description[:50]}"
