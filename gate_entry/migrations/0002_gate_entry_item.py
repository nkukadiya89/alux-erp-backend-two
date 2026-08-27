from decimal import Decimal
import uuid

from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ("gate_entry", "0001_initial_gate_entry"),
    ]

    operations = [
        migrations.CreateModel(
            name="GateEntryItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
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
                    "gate_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        db_index=True,
                        to="gate_entry.gateentry",
                    ),
                ),
            ],
            options={
                "db_table": "gate_entry_item",
                "ordering": ["id"],
            },
        ),
    ]
