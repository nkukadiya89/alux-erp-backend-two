from django.db import migrations


def resync_jobwork_stages(apps, schema_editor):
    from workorder.process_tracking import resync_all_jobwork_stages

    resync_all_jobwork_stages(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0024_backfill_process_tracking"),
    ]

    operations = [
        migrations.RunPython(resync_jobwork_stages, noop_reverse),
    ]
