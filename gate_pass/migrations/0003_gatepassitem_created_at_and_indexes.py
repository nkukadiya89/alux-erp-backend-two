# Gate Pass audit: GatePassItem created_at, GatePass composite index (ERP standard)

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        (
            "gate_pass",
            "0002_rename_gate_pass_no_idx_gate_pass_gate_pa_ae2e5f_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="gatepassitem",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, default=timezone.now
            ),
        ),
        migrations.AddIndex(
            model_name="gatepass",
            index=models.Index(
                fields=["deleted", "is_archived"],
                name="gate_pass_deleted_is_archived_idx",
            ),
        ),
    ]
