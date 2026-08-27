from django.db import migrations
from django.utils import timezone


def drop_default_open_stage(apps, schema_editor):
    """
    Soft-delete Open stage rows created by default on SO → WO create
    when WO status is not Open. Resync so Next Pending becomes Planning.
    """
    from workorder.models import WorkOrderProcessStage
    from workorder.process_tracking import resync_all_jobwork_stages

    now = timezone.now()
    WorkOrderProcessStage.objects.filter(
        deleted=False,
        stage_code="OPEN",
    ).exclude(track__workorder__status="Open").update(
        deleted=True,
        deleted_at=now,
        is_applicable=False,
        updated_at=now,
    )

    resync_all_jobwork_stages(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0028_drop_default_approval_stages"),
    ]

    operations = [
        migrations.RunPython(drop_default_open_stage, noop_reverse),
    ]
