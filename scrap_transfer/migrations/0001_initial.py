# Initial migration for Scrap Transfer module.

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
            name="ScrapTransfer",
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
                    "transfer_no",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("transfer_date", models.DateField(db_index=True)),
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
                            ("SUBMITTED", "Submitted"),
                            ("COMPLETED", "Completed"),
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
                    "from_store",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_transfers_out",
                        to="store.store",
                    ),
                ),
                (
                    "to_plant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_transfers",
                        to="common.plant",
                    ),
                ),
                (
                    "to_store",
                    models.ForeignKey(
                        db_index=True,
                        help_text="Destination store (Melting WIP) under to_plant.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_transfers_in",
                        to="store.store",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_transfers_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scrap_transfers_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "scrap_transfer",
                "ordering": ["-transfer_date", "-created_at"],
                "verbose_name": "Scrap Transfer",
                "verbose_name_plural": "Scrap Transfers",
            },
        ),
        migrations.CreateModel(
            name="ScrapTransferItem",
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
                ("batch_heat", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "transfer_qty",
                    models.DecimalField(
                        decimal_places=4,
                        max_digits=18,
                        validators=[MinValueValidator(Decimal("0.0001"))],
                    ),
                ),
                ("remarks", models.TextField(blank=True, null=True)),
                (
                    "scrap_transfer",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="scrap_transfer.scraptransfer",
                    ),
                ),
                (
                    "scrap_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_transfer_items",
                        to="product.item",
                    ),
                ),
                (
                    "uom",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scrap_transfer_items",
                        to="common.uom",
                    ),
                ),
            ],
            options={
                "db_table": "scrap_transfer_item",
                "ordering": ["id"],
                "verbose_name": "Scrap Transfer Item",
                "verbose_name_plural": "Scrap Transfer Items",
            },
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["transfer_no"], name="scrap_trans_transfer_8a1b2c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(fields=["status"], name="scrap_trans_status_9d2e3f_idx"),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["transfer_date"], name="scrap_trans_transfer_4e5f6g_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["from_store_id"], name="scrap_trans_from_st_7h8i9j_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["to_plant_id"], name="scrap_trans_to_pla_0k1l2m_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["to_store_id"], name="scrap_trans_to_sto_3n4o5p_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["is_archived"], name="scrap_trans_is_arch_6q7r8s_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransfer",
            index=models.Index(
                fields=["status", "is_archived"], name="scrap_trans_status_9t0u1v_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransferitem",
            index=models.Index(
                fields=["scrap_transfer_id"], name="scrap_trans_scrap_t_2w3x4y_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scraptransferitem",
            index=models.Index(
                fields=["scrap_item_id"], name="scrap_trans_scrap_i_5z6a7b_idx"
            ),
        ),
    ]
