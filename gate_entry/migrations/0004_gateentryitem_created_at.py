# Audit field: created_at on GateEntryItem (coding standards - audit fields in all tables)

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("gate_entry", "0003_gateentry_is_archived"),
    ]

    operations = [
        migrations.AddField(
            model_name="gateentryitem",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                default=timezone.now,
            ),
        ),
    ]
