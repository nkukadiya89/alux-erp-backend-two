"""
Scrap Entry module models.
Record scrap from production, increase scrap store inventory, heat traceability.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class ScrapType(models.Model):
    """Master for scrap type. Optional link to ItemCategory for validation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(
        "common.ItemCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_types",
        db_index=True,
        help_text="If set, only items of this category can use this scrap type.",
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_type_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_type_updated",
    )

    class Meta:
        db_table = "scrap_type"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_archived"]),
        ]
        verbose_name = "Scrap Type"
        verbose_name_plural = "Scrap Types"

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class Process(models.Model):
    """Master for process/source process (e.g. extrusion, cutting)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_updated",
    )

    class Meta:
        db_table = "process"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_archived"]),
        ]
        verbose_name = "Process"
        verbose_name_plural = "Processes"

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ScrapStoreStock(models.Model):
    """Scrap store quantity per store + item. Increased on Scrap Entry post."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "store.Store",
        on_delete=models.PROTECT,
        related_name="scrap_stock",
        db_index=True,
    )
    item = models.ForeignKey(
        "product.Item",
        on_delete=models.PROTECT,
        related_name="scrap_store_stock",
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        db_index=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scrap_store_stock"
        ordering = ["store", "item"]
        unique_together = [["store", "item"]]
        indexes = [
            models.Index(fields=["store", "item"]),
        ]
        verbose_name = "Scrap Store Stock"
        verbose_name_plural = "Scrap Store Stocks"

    def __str__(self):
        return f"{self.store.store_code} - {self.item.item_code}: {self.quantity}"


class ScrapEntry(models.Model):
    """
    Scrap entry header. Status: DRAFT -> POSTED -> TRANSFERRED.
    References: Plant, Department (source_department). Line items reference ScrapType and Process masters.
    """

    STATUS_DRAFT = "DRAFT"
    STATUS_POSTED = "POSTED"
    STATUS_TRANSFERRED = "TRANSFERRED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_POSTED, "Posted"),
        (STATUS_TRANSFERRED, "Transferred"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry_no = models.CharField(max_length=50, unique=True, db_index=True)
    date = models.DateField(db_index=True)
    plant = models.ForeignKey(
        "common.Plant",
        on_delete=models.PROTECT,
        related_name="scrap_entries",
        db_index=True,
    )
    source_department = models.ForeignKey(
        "common.Department",
        on_delete=models.PROTECT,
        related_name="scrap_entries",
        null=True,
        blank=True,
        db_index=True,
    )
    source_ref = models.CharField(max_length=100, blank=True, null=True, db_index=True)
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
        related_name="scrap_entries_created",
    )
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_entries_updated",
    )

    class Meta:
        db_table = "scrap_entry"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["entry_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["date"]),
            models.Index(fields=["plant_id"]),
            models.Index(fields=["source_department_id"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["status", "is_archived"]),
        ]
        verbose_name = "Scrap Entry"
        verbose_name_plural = "Scrap Entries"

    def __str__(self):
        return self.entry_no

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ScrapEntryItem(models.Model):
    """Line item for scrap entry. References ScrapType and Process masters."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scrap_entry = models.ForeignKey(
        ScrapEntry,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    item = models.ForeignKey(
        "product.Item",
        on_delete=models.PROTECT,
        related_name="scrap_entry_items",
        db_index=True,
    )
    scrap_type = models.ForeignKey(
        ScrapType,
        on_delete=models.PROTECT,
        related_name="scrap_entry_items",
        db_index=True,
        help_text="Reference to Scrap Type master.",
    )
    qty = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    uom = models.ForeignKey(
        "common.UOM",
        on_delete=models.PROTECT,
        related_name="scrap_entry_items",
        db_index=True,
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.PROTECT,
        related_name="scrap_entry_items",
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference to Process master (source process e.g. Extrusion, Cutting).",
    )
    from_process = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Free text when Process master is not selected; or override display.",
    )
    store = models.ForeignKey(
        "store.Store",
        on_delete=models.PROTECT,
        related_name="scrap_entry_items",
        db_index=True,
    )
    batch_heat = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "scrap_entry_item"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["scrap_entry_id"]),
            models.Index(fields=["item_id"]),
            models.Index(fields=["scrap_type_id"]),
            models.Index(fields=["store_id"]),
            models.Index(fields=["process_id"]),
        ]
        verbose_name = "Scrap Entry Item"
        verbose_name_plural = "Scrap Entry Items"

    def __str__(self):
        return f"{self.scrap_entry.entry_no} - {self.item.item_code}"
