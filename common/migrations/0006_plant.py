# Generated manually for Plant Master module

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("common", "0005_packingmode_created_at_packingmode_created_by_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plant",
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
                    "plant_code",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("plant_name", models.CharField(max_length=255)),
                (
                    "plant_type",
                    models.CharField(
                        choices=[
                            ("Extrusion", "Extrusion"),
                            ("Assembly", "Assembly"),
                            ("Warehouse", "Warehouse"),
                            ("Site", "Site"),
                            ("Office", "Office"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Inactive", "Inactive")],
                        db_index=True,
                        default="Active",
                        max_length=20,
                    ),
                ),
                ("address_line_1", models.CharField(max_length=255)),
                (
                    "address_line_2",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("city", models.CharField(db_index=True, max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("country", models.CharField(max_length=100)),
                ("postal_code", models.CharField(max_length=20)),
                ("phone_number", models.CharField(max_length=20)),
                ("email", models.EmailField(max_length=255)),
                ("plant_head_name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="plant_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="plant_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "plant",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="plant",
            index=models.Index(fields=["plant_code"], name="plant_plant_code_idx"),
        ),
        migrations.AddIndex(
            model_name="plant",
            index=models.Index(fields=["status"], name="plant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="plant",
            index=models.Index(fields=["city"], name="plant_city_idx"),
        ),
        migrations.AddIndex(
            model_name="plant",
            index=models.Index(
                fields=["deleted", "status"], name="plant_deleted_status_idx"
            ),
        ),
    ]
