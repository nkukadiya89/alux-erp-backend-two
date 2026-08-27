# Gate Entry → GRN conversion: is_converted, grn_reference

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0045_rename_grn_status_idx_grn_status_5ca68c_idx_and_more"),
        ("gate_entry", "0004_gateentryitem_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="gateentry",
            name="is_converted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="gateentry",
            name="grn_reference",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="gate_entries",
                to="common.grn",
                db_index=True,
            ),
        ),
        migrations.AddIndex(
            model_name="gateentry",
            index=models.Index(
                fields=["is_converted"],
                name="gate_entry_is_conv_67e8fa_idx",
            ),
        ),
    ]
