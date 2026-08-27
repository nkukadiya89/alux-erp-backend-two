# Add Process FK to ScrapEntryItem and indexes for master refs

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("scrap_entry", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="scrapentryitem",
            name="process",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                help_text="Reference to Process master (source process e.g. Extrusion, Cutting).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="scrap_entry_items",
                to="scrap_entry.process",
            ),
        ),
        migrations.AddIndex(
            model_name="scrapentryitem",
            index=models.Index(
                fields=["scrap_type_id"], name="scrap_entry_item_st_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapentryitem",
            index=models.Index(fields=["process_id"], name="scrap_entry_item_pr_idx"),
        ),
    ]
