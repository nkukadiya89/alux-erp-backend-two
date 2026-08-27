"""
Scrap Sale module models.
Aluminum Extrusion Manufacturing ERP - external scrap sale with stock reduction and audit.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class ScrapItem(models.Model):
    """Master data for scrap item types. Used in scrap sale line items and stock."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_code = models.CharField(max_length=50, unique=True, db_index=True)
    item_name = models.CharField(max_length=255, db_index=True)
    uom = models.ForeignKey(
        "common.UOM",
        on_delete=models.PROTECT,
        related_name="scrap_items",
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
        related_name="scrap_items_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_items_updated",
    )

    class Meta:
        db_table = "scrap_item"
        ordering = ["item_code"]
        indexes = [
            models.Index(fields=["item_code"]),
            models.Index(fields=["is_archived"]),
        ]
        verbose_name = "Scrap Item"
        verbose_name_plural = "Scrap Items"

    def __str__(self):
        return f"{self.item_code} - {self.item_name}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ScrapStock(models.Model):
    """Current scrap store quantity per scrap item. Reduced on sale finalize."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scrap_item = models.OneToOneField(
        ScrapItem,
        on_delete=models.CASCADE,
        related_name="stock",
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
        db_table = "scrap_stock"
        verbose_name = "Scrap Stock"
        verbose_name_plural = "Scrap Stocks"

    def __str__(self):
        return f"{self.scrap_item.item_code}: {self.quantity}"


class ScrapSale(models.Model):
    """Scrap sale header. Status: DRAFT -> FINALIZED (stock + ledger) or CANCELLED."""

    STATUS_DRAFT = "DRAFT"
    STATUS_FINALIZED = "FINALIZED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_FINALIZED, "Finalized"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale_no = models.CharField(max_length=50, unique=True, db_index=True)
    sale_date = models.DateField(db_index=True)
    customer = models.ForeignKey(
        "customer.Customer",
        on_delete=models.PROTECT,
        related_name="scrap_sales",
        db_index=True,
    )
    dispatch_ref = models.CharField(
        max_length=100, blank=True, null=True, db_index=True
    )
    remarks = models.TextField(blank=True, null=True)
    total_qty = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    total_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
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
        related_name="scrap_sales_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_sales_updated",
    )

    class Meta:
        db_table = "scrap_sale"
        ordering = ["-sale_date", "-created_at"]
        indexes = [
            models.Index(fields=["sale_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sale_date"]),
            models.Index(fields=["customer_id"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["status", "is_archived"]),
        ]
        verbose_name = "Scrap Sale"
        verbose_name_plural = "Scrap Sales"

    def __str__(self):
        return self.sale_no

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ScrapSaleItem(models.Model):
    """Line item for a scrap sale. total_value = sale_qty * rate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scrap_sale = models.ForeignKey(
        ScrapSale,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    scrap_item = models.ForeignKey(
        ScrapItem,
        on_delete=models.PROTECT,
        related_name="sale_items",
        db_index=True,
    )
    sale_qty = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    uom = models.ForeignKey(
        "common.UOM",
        on_delete=models.PROTECT,
        related_name="scrap_sale_items",
        db_index=True,
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )
    total_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "scrap_sale_item"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["scrap_sale_id"]),
            models.Index(fields=["scrap_item_id"]),
        ]
        verbose_name = "Scrap Sale Item"
        verbose_name_plural = "Scrap Sale Items"

    def __str__(self):
        return f"{self.scrap_sale.sale_no} - {self.scrap_item.item_code}"

    def save(self, *args, **kwargs):
        if self.rate is not None and self.sale_qty is not None:
            self.total_value = (self.sale_qty * self.rate).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
