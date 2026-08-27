from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GatePass",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, default=uuid.uuid4, editable=False
                    ),
                ),
                (
                    "gate_pass_no",
                    models.CharField(max_length=50, unique=True, db_index=True),
                ),
                ("date", models.DateField(db_index=True)),
                (
                    "type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("RETURNABLE", "Returnable"),
                            ("NON_RETURNABLE", "Non Returnable"),
                        ],
                        db_index=True,
                    ),
                ),
                (
                    "po_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Optional Purchase Order ID (UUID). Stored as raw UUID to avoid hard coupling to procurement app.",
                    ),
                ),
                ("party_name", models.CharField(max_length=255, db_index=True)),
                ("vehicle_no", models.CharField(max_length=50, db_index=True)),
                ("remarks", models.TextField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("DRAFT", "Draft"),
                            ("PENDING", "Pending"),
                            ("IN_PROCESS", "In Process"),
                            ("CLOSED", "Closed"),
                        ],
                        default="DRAFT",
                        db_index=True,
                    ),
                ),
                ("is_archived", models.BooleanField(default=False, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(null=True, blank=True)),
                ("deleted", models.BooleanField(default=False, db_index=True)),
                ("deleted_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={
                "db_table": "gate_pass",
                "ordering": ["-date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="GatePassItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, default=uuid.uuid4, editable=False
                    ),
                ),
                ("description", models.TextField()),
                ("unit", models.CharField(max_length=50)),
                (
                    "qty",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=4,
                        validators=[MinValueValidator(Decimal("0.0001"))],
                    ),
                ),
                ("purpose", models.TextField(blank=True, null=True)),
                (
                    "gate_pass",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        db_index=True,
                        to="gate_pass.gatepass",
                    ),
                ),
            ],
            options={
                "db_table": "gate_pass_item",
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="gatepass",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                related_name="gate_passes_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="gatepass",
            name="deleted_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="gate_passes_deleted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="gatepass",
            name="updated_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="gate_passes_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(fields=["gate_pass_no"], name="gate_pass_no_idx"),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(fields=["status"], name="gate_pass_status_idx"),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(fields=["date"], name="gate_pass_date_idx"),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(fields=["po_id"], name="gate_pass_po_idx"),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(fields=["party_name"], name="gate_pass_party_idx"),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(fields=["vehicle_no"], name="gate_pass_vehicle_idx"),
        ),
    ]
