from django.db import migrations
from django.utils import timezone


def prune_unselected_stages(apps, schema_editor):
    """
    Soft-delete process stage rows that are not selected for the item
    (is_applicable=False), and resync tracks from Surface Finish selection.
    """
    from workorder.process_tracking import resync_all_jobwork_stages
    from workorder.models import WorkOrderProcessStage

    now = timezone.now()
    WorkOrderProcessStage.objects.filter(
        deleted=False, is_applicable=False
    ).update(deleted=True, deleted_at=now, updated_at=now)

    resync_all_jobwork_stages(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0026_alter_process_status_jobwork_choices"),
    ]

    operations = [
        migrations.RunPython(prune_unselected_stages, noop_reverse),
    ]
