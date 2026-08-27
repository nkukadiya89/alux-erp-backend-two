# Gate Entry audit: add is_archived per ERP standard

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gate_entry", "0002_gate_entry_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="gateentry",
            name="is_archived",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["deleted", "is_archived"],
                name="gate_entry_deleted_is_arch_idx",
            ),
        ),
    ]
