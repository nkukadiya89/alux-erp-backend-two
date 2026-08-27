# Generated migration for Plant Capability architecture

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "common",
            "0007_rename_plant_plant_code_idx_plant_plant_c_4ddeb9_idx_and_more",
        ),
    ]

    operations = [
        # Create PlantType model
        migrations.CreateModel(
            name="PlantType",
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
                    "code",
                    models.CharField(
                        db_index=True,
                        help_text="Uppercase code like EXTRUSION, WAREHOUSE",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Inactive", "Inactive")],
                        db_index=True,
                        default="Active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
            ],
            options={
                "db_table": "plant_type",
                "ordering": ["code"],
            },
        ),
        migrations.AddIndex(
            model_name="planttype",
            index=models.Index(fields=["code"], name="plant_type_code_idx"),
        ),
        migrations.AddIndex(
            model_name="planttype",
            index=models.Index(fields=["status"], name="plant_type_status_idx"),
        ),
        migrations.AddIndex(
            model_name="planttype",
            index=models.Index(
                fields=["is_deleted", "status"], name="plant_type_deleted_status_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="planttype",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=["code"],
                name="unique_active_plant_type_code",
            ),
        ),
        # Create PlantCapability model
        migrations.CreateModel(
            name="PlantCapability",
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
                    "code",
                    models.CharField(
                        db_index=True,
                        help_text="Uppercase code like PRODUCTION, INVENTORY",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Inactive", "Inactive")],
                        db_index=True,
                        default="Active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
            ],
            options={
                "db_table": "plant_capability",
                "ordering": ["code"],
                "verbose_name": "Plant Capability",
                "verbose_name_plural": "Plant Capabilities",
            },
        ),
        migrations.AddIndex(
            model_name="plantcapability",
            index=models.Index(fields=["code"], name="plant_capability_code_idx"),
        ),
        migrations.AddIndex(
            model_name="plantcapability",
            index=models.Index(fields=["status"], name="plant_capability_status_idx"),
        ),
        migrations.AddIndex(
            model_name="plantcapability",
            index=models.Index(
                fields=["is_deleted", "status"],
                name="plant_capability_deleted_status_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="plantcapability",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=["code"],
                name="unique_active_plant_capability_code",
            ),
        ),
        # Create PlantTypeCapability model
        migrations.CreateModel(
            name="PlantTypeCapability",
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
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Inactive", "Inactive")],
                        db_index=True,
                        default="Active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "capability",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="plant_types",
                        to="common.plantcapability",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="plant_type_capability_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "plant_type",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="capabilities",
                        to="common.planttype",
                    ),
                ),
            ],
            options={
                "db_table": "plant_type_capability",
                "ordering": ["plant_type__code", "capability__code"],
                "verbose_name": "Plant Type Capability",
                "verbose_name_plural": "Plant Type Capabilities",
            },
        ),
        migrations.AddIndex(
            model_name="planttypecapability",
            index=models.Index(
                fields=["plant_type", "capability"],
                name="plant_type_capability_type_cap_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="planttypecapability",
            index=models.Index(
                fields=["status"], name="plant_type_capability_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="planttypecapability",
            index=models.Index(
                fields=["is_deleted", "status"],
                name="plant_type_capability_deleted_status_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="planttypecapability",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=["plant_type", "capability"],
                name="unique_active_plant_type_capability",
            ),
        ),
    ]
