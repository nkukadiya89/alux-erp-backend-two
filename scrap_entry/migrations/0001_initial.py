# Initial migration for Scrap Entry module.
# Creates ScrapType, Process, ScrapStoreStock, ScrapEntry, ScrapEntryItem.

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("common", "0046_grn_gate_entry_invoice_no_grnitem_batch_heat"),
        (
            "product",
            "0055_remove_temper_unique_active_temper_name_code_section_and_more",
        ),
        ("store", "0004_alter_store_store_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ScrapType",
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
                ("code", models.CharField(db_index=True, max_length=50, unique=True)),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("is_archived", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        help_text="If set, only items of this category can use this scrap type.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_types",
                        to="common.itemcategory",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_type_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_type_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "scrap_type",
                "ordering": ["code"],
                "verbose_name": "Scrap Type",
                "verbose_name_plural": "Scrap Types",
            },
        ),
        migrations.CreateModel(
            name="Process",
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
                ("code", models.CharField(db_index=True, max_length=50, unique=True)),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("is_archived", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="process_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="process_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "process",
                "ordering": ["code"],
                "verbose_name": "Process",
                "verbose_name_plural": "Processes",
            },
        ),
        migrations.CreateModel(
            name="ScrapEntry",
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
                    "entry_no",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("date", models.DateField(db_index=True)),
                (
                    "source_ref",
                    models.CharField(
                        blank=True, db_index=True, max_length=100, null=True
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
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("POSTED", "Posted"),
                            ("TRANSFERRED", "Transferred"),
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
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_entries_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "plant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_entries",
                        to="common.plant",
                    ),
                ),
                (
                    "source_department",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_entries",
                        to="common.department",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_entries_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "scrap_entry",
                "ordering": ["-date", "-created_at"],
                "verbose_name": "Scrap Entry",
                "verbose_name_plural": "Scrap Entries",
            },
        ),
        migrations.CreateModel(
            name="ScrapStoreStock",
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
                    "item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_store_stock",
                        to="product.item",
                    ),
                ),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_stock",
                        to="store.store",
                    ),
                ),
            ],
            options={
                "db_table": "scrap_store_stock",
                "ordering": ["store", "item"],
                "verbose_name": "Scrap Store Stock",
                "verbose_name_plural": "Scrap Store Stocks",
            },
        ),
        migrations.CreateModel(
            name="ScrapEntryItem",
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
                    "qty",
                    models.DecimalField(
                        decimal_places=4,
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0.0001"))],
                    ),
                ),
                (
                    "from_process",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("batch_heat", models.CharField(blank=True, max_length=100, null=True)),
                ("remarks", models.TextField(blank=True, null=True)),
                (
                    "item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_entry_items",
                        to="product.item",
                    ),
                ),
                (
                    "scrap_entry",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="scrap_entry.scrapentry",
                    ),
                ),
                (
                    "scrap_type",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_entry_items",
                        to="scrap_entry.scraptype",
                    ),
                ),
                (
                    "store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_entry_items",
                        to="store.store",
                    ),
                ),
                (
                    "uom",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_entry_items",
                        to="common.uom",
                    ),
                ),
            ],
            options={
                "db_table": "scrap_entry_item",
                "ordering": ["id"],
                "verbose_name": "Scrap Entry Item",
                "verbose_name_plural": "Scrap Entry Items",
            },
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(fields=["entry_no"], name="scrap_entry_entry_no_idx"),
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(fields=["status"], name="scrap_entry_status_idx"),
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(fields=["date"], name="scrap_entry_date_idx"),
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(fields=["plant_id"], name="scrap_entry_plant_id_idx"),
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(
                fields=["source_department_id"], name="scrap_entry_src_dept_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(
                fields=["is_archived"], name="scrap_entry_is_archived_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapentry",
            index=models.Index(
                fields=["status", "is_archived"], name="scrap_entry_status_arch_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapentryitem",
            index=models.Index(
                fields=["scrap_entry_id"], name="scrap_entry_item_entry_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapentryitem",
            index=models.Index(fields=["item_id"], name="scrap_entry_item_item_idx"),
        ),
        migrations.AddIndex(
            model_name="scrapentryitem",
            index=models.Index(fields=["store_id"], name="scrap_entry_item_store_idx"),
        ),
        migrations.AddConstraint(
            model_name="scrapstorestock",
            constraint=models.UniqueConstraint(
                fields=("store", "item"),
                name="scrap_store_stock_store_item_uniq",
            ),
        ),
    ]
