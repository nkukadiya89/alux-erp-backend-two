# Generated manually - Change plant_head_name to plant_head ForeignKey

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0015_plant_plant_created_dea005_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="plant",
            name="plant_head_name",
        ),
        migrations.AddField(
            model_name="plant",
            name="plant_head",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                help_text="Plant head user (must have Plant Head role)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="plants_headed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="plant",
            index=models.Index(fields=["plant_head"], name="plant_plant_head_idx"),
        ),
    ]
