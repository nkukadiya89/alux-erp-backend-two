# Generated manually for Gate Entry module

from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("transporter", "0008_alter_transporter_updated_at"),
        ("vendor", "0004_alter_vendor_updated_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="GateEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                (
                    "gate_entry_no",
                    models.CharField(
                        db_index=True,
                        editable=False,
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                ("driver_name", models.CharField(db_index=True, max_length=255)),
                (
                    "driver_mobile_no",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("vehicle_no", models.CharField(db_index=True, max_length=50)),
                (
                    "challan_no",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "invoice_no",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("inward_time", models.TimeField()),
                ("outward_time", models.TimeField(blank=True, null=True)),
                (
                    "empty_vehicle_weight",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        help_text="Required before closing gate entry.",
                        max_digits=14,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0"))
                        ],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("in_company", "In Company"),
                            ("close", "Close"),
                        ],
                        db_index=True,
                        default="in_company",
                        max_length=20,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "transporter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gate_entries",
                        to="transporter.transporter",
                    ),
                ),
                (
                    "vendor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gate_entries",
                        to="vendor.vendor",
                    ),
                ),
            ],
            options={
                "db_table": "gate_entry",
                "ordering": ["-date", "-created_at"],
                "verbose_name": "Gate Entry",
                "verbose_name_plural": "Gate Entries",
            },
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["gate_entry_no"], name="gate_entry_gate_en_7a1b2c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(fields=["date"], name="gate_entry_date_8b2c3d_idx"),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(fields=["status"], name="gate_entry_status_9c3d4e_idx"),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["vendor_id"], name="gate_entry_vendor__0d4e5f_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["transporter_id"], name="gate_entry_transpo_1e5f6a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["vehicle_no"], name="gate_entry_vehicle_2f6a7b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["deleted", "-created_at"],
                name="gate_entry_deleted_3a7b8c_idx",
            ),
        ),
    ]
