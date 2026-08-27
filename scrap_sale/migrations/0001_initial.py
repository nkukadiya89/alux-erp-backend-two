# Merged initial migration for Scrap Sale module.
# Creates ScrapItem, ScrapStock, ScrapSale (final schema), ScrapSaleItem.

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("common", "0025_uom_deleted_at"),
        ("customer", "0025_remove_customer_customer_cu_custome_d3a0b9_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ScrapItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "item_code",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("item_name", models.CharField(db_index=True, max_length=255)),
                ("is_archived", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "uom",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_items",
                        to="common.uom",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_items_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_items_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "scrap_item",
                "ordering": ["item_code"],
                "verbose_name": "Scrap Item",
                "verbose_name_plural": "Scrap Items",
            },
        ),
        migrations.CreateModel(
            name="ScrapStock",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        db_index=True,
                        decimal_places=4,
                        default=Decimal("0"),
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "scrap_item",
                    models.OneToOneField(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock",
                        to="scrap_sale.scrapitem",
                    ),
                ),
            ],
            options={
                "db_table": "scrap_stock",
                "verbose_name": "Scrap Stock",
                "verbose_name_plural": "Scrap Stocks",
            },
        ),
        migrations.CreateModel(
            name="ScrapSale",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "sale_no",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("sale_date", models.DateField(db_index=True)),
                (
                    "dispatch_ref",
                    models.CharField(
                        blank=True, max_length=100, null=True, db_index=True
                    ),
                ),
                ("remarks", models.TextField(blank=True, null=True)),
                (
                    "total_qty",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0"),
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "total_value",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("FINALIZED", "Finalized"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("is_archived", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "customer",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_sales",
                        to="customer.customer",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_sales_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_sales_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "scrap_sale",
                "ordering": ["-sale_date", "-created_at"],
                "verbose_name": "Scrap Sale",
                "verbose_name_plural": "Scrap Sales",
            },
        ),
        migrations.CreateModel(
            name="ScrapSaleItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "sale_qty",
                    models.DecimalField(
                        decimal_places=4,
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0.0001"))],
                    ),
                ),
                (
                    "rate",
                    models.DecimalField(
                        decimal_places=4,
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "total_value",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("remarks", models.TextField(blank=True, null=True)),
                (
                    "scrap_sale",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="scrap_sale.scrapsale",
                    ),
                ),
                (
                    "scrap_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sale_items",
                        to="scrap_sale.scrapitem",
                    ),
                ),
                (
                    "uom",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_sale_items",
                        to="common.uom",
                    ),
                ),
            ],
            options={
                "db_table": "scrap_sale_item",
                "ordering": ["id"],
                "verbose_name": "Scrap Sale Item",
                "verbose_name_plural": "Scrap Sale Items",
            },
        ),
    ]
