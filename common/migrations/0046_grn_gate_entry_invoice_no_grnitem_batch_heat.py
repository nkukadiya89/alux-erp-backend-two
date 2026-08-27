# GRN from Gate Entry: gate_entry FK, invoice_no; GRNItem batch_heat

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gate_entry", "0005_gateentry_is_converted_grn_reference"),
        ("common", "0045_rename_grn_status_idx_grn_status_5ca68c_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="grn",
            name="invoice_no",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="grn",
            name="gate_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="grns_from_gate_entry",
                to="gate_entry.gateentry",
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="grnitem",
            name="batch_heat",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
