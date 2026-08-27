# Generated manually to make plant field nullable in Department model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0018_department"),
    ]

    operations = [
        migrations.AlterField(
            model_name="department",
            name="plant",
            field=models.ForeignKey(
                blank=True,
                help_text="Plant this department belongs to (optional)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="departments",
                to="common.plant",
                db_index=True,
            ),
        ),
    ]
