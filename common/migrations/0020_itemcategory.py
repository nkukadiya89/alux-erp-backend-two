# Generated manually for Item Category Master

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0019_make_department_plant_nullable"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemCategory",
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
                    "category_code",
                    models.CharField(
                        db_index=True,
                        help_text="Unique category code",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("category_name", models.CharField(db_index=True, max_length=255)),
                (
                    "allowed_item_type",
                    models.CharField(
                        choices=[
                            ("RAW", "Raw Material"),
                            ("CONSUMABLE", "Consumable"),
                            ("SEMI", "Semi-Finished"),
                            ("FG", "Finished Goods"),
                            ("SPARE", "Spare Parts"),
                            ("SCRAP", "Scrap"),
                            ("TOOLING", "Tooling"),
                        ],
                        db_index=True,
                        help_text="Allowed item type for this category",
                        max_length=20,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Category description", null=True
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_archived", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="itemcategory_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="itemcategory_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Item Category",
                "verbose_name_plural": "Item Categories",
                "db_table": "item_category",
                "ordering": ["category_code"],
                "indexes": [
                    models.Index(
                        fields=["category_code"], name="item_categor_categor_idx"
                    ),
                    models.Index(
                        fields=["category_name"], name="item_categor_categor_name_idx"
                    ),
                    models.Index(
                        fields=["allowed_item_type"], name="item_categor_allowed_idx"
                    ),
                    models.Index(fields=["is_active"], name="item_categor_is_acti_idx"),
                    models.Index(
                        fields=["is_archived", "is_active"],
                        name="item_categor_is_arch_idx",
                    ),
                    models.Index(
                        fields=["created_by"], name="item_categor_created_idx"
                    ),
                    models.Index(
                        fields=["updated_by"], name="item_categor_updated_idx"
                    ),
                    models.Index(
                        fields=["created_at"], name="item_categor_created_at_idx"
                    ),
                    models.Index(
                        fields=["allowed_item_type", "is_archived", "is_active"],
                        name="item_categor_allowed_type_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_archived", False)),
                        fields=["category_code"],
                        name="unique_active_item_category_code",
                    ),
                ],
            },
        ),
    ]
