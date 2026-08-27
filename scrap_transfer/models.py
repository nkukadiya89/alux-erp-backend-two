"""
Scrap Transfer module models.
Internal transfer of scrap from Scrap Store to Melting Plant (WIP).
Reduces scrap store stock, increases melting WIP stock, full heat traceability.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class ScrapTransfer(models.Model):
    """
    Scrap transfer header. Status: DRAFT -> SUBMITTED -> COMPLETED.
    Moves scrap from from_store (scrap type) to to_store (melting WIP) under to_plant.
    """

    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_COMPLETED, "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer_no = models.CharField(max_length=50, unique=True, db_index=True)
    transfer_date = models.DateField(db_index=True)
    from_store = models.ForeignKey(
        "store.Store",
        on_delete=models.PROTECT,
        related_name="scrap_transfers_out",
        db_index=True,
    )
    to_plant = models.ForeignKey(
        "common.Plant",
        on_delete=models.PROTECT,
        related_name="scrap_transfers",
        db_index=True,
    )
    to_store = models.ForeignKey(
        "store.Store",
        on_delete=models.PROTECT,
        related_name="scrap_transfers_in",
        db_index=True,
        help_text="Destination store (Melting WIP) under to_plant.",
    )
    remarks = models.TextField(blank=True, null=True)
    total_qty = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_transfers_created",
    )
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_transfers_updated",
    )

    class Meta:
        db_table = "scrap_transfer"
        ordering = ["-transfer_date", "-created_at"]
        indexes = [
            models.Index(fields=["transfer_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["transfer_date"]),
            models.Index(fields=["from_store_id"]),
            models.Index(fields=["to_plant_id"]),
            models.Index(fields=["to_store_id"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["status", "is_archived"]),
        ]
        verbose_name = "Scrap Transfer"
        verbose_name_plural = "Scrap Transfers"

    def __str__(self):
        return self.transfer_no

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ScrapTransferItem(models.Model):
    """Line item for scrap transfer. transfer_qty <= available scrap in from_store."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scrap_transfer = models.ForeignKey(
        ScrapTransfer,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    scrap_item = models.ForeignKey(
        "product.Item",
        on_delete=models.PROTECT,
        related_name="scrap_transfer_items",
        db_index=True,
    )
    batch_heat = models.CharField(max_length=100, blank=True, null=True)
    transfer_qty = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    uom = models.ForeignKey(
        "common.UOM",
        on_delete=models.PROTECT,
        related_name="scrap_transfer_items",
        db_index=True,
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "scrap_transfer_item"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["scrap_transfer_id"]),
            models.Index(fields=["scrap_item_id"]),
        ]
        verbose_name = "Scrap Transfer Item"
        verbose_name_plural = "Scrap Transfer Items"

    def __str__(self):
        return f"{self.scrap_transfer.transfer_no} - {self.scrap_item.item_code}"
