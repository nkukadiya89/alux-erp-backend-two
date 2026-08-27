"""
Scrap Generation Remelt module models.
Tracks remelt conversion from source inventory to scrap store stock.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class ScrapGenerationRemelt(models.Model):
    """
    Remelt header.
    Status flow: DRAFT -> SUBMITTED -> COMPLETED.
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
    remelt_no = models.CharField(max_length=50, unique=True, db_index=True)
    remelt_date = models.DateField(db_index=True)
    plant = models.ForeignKey(
        "common.Plant",
        on_delete=models.PROTECT,
        related_name="scrap_generation_remelts",
        db_index=True,
    )
    source_store = models.ForeignKey(
        "store.Store",
        on_delete=models.PROTECT,
        related_name="scrap_generation_remelts_out",
        db_index=True,
    )
    destination_store = models.ForeignKey(
        "store.Store",
        on_delete=models.PROTECT,
        related_name="scrap_generation_remelts_in",
        db_index=True,
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
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_generation_remelts_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_generation_remelts_updated",
    )

    class Meta:
        db_table = "scrap_generation_remelt"
        ordering = ["-remelt_date", "-created_at"]
        indexes = [
            models.Index(fields=["remelt_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["remelt_date"]),
            models.Index(fields=["plant_id"]),
            models.Index(fields=["source_store_id"]),
            models.Index(fields=["destination_store_id"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["status", "is_archived"]),
        ]
        verbose_name = "Scrap Generation Remelt"
        verbose_name_plural = "Scrap Generation Remelts"

    def __str__(self):
        return self.remelt_no

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ScrapGenerationRemeltItem(models.Model):
    """Line item for remelt generation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scrap_generation_remelt = models.ForeignKey(
        ScrapGenerationRemelt,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    item = models.ForeignKey(
        "product.Item",
        on_delete=models.PROTECT,
        related_name="scrap_generation_remelt_items",
        db_index=True,
    )
    batch_heat = models.CharField(max_length=100, blank=True, null=True)
    qty = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    uom = models.ForeignKey(
        "common.UOM",
        on_delete=models.PROTECT,
        related_name="scrap_generation_remelt_items",
        db_index=True,
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "scrap_generation_remelt_item"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["scrap_generation_remelt_id"]),
            models.Index(fields=["item_id"]),
        ]
        verbose_name = "Scrap Generation Remelt Item"
        verbose_name_plural = "Scrap Generation Remelt Items"

    def __str__(self):
        return f"{self.scrap_generation_remelt.remelt_no} - {self.item.item_code}"
