from django.db import migrations


def backfill_process_tracks(apps, schema_editor):
    """
    Create process tracks for existing live workorders without changing
    legacy WorkOrder.status / WorkOrderDetail.status values.
    """
    # Use service layer against real models so inference helpers work.
    from workorder.process_tracking import backfill_existing_workorders

    backfill_existing_workorders(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0023_process_tracking"),
    ]

    operations = [
        migrations.RunPython(backfill_process_tracks, noop_reverse),
    ]
