from django.db import migrations
from django.utils import timezone


def drop_default_approval_stages(apps, schema_editor):
    """
    Soft-delete Marketing / Design / Management approval stage rows that were
    created by default on SO → WO create (WO was not in an approval status).
    Then resync pipelines so Next Pending becomes Open / Planning.
    """
    from workorder.models import WorkOrderProcessStage
    from workorder.process_tracking import resync_all_jobwork_stages

    now = timezone.now()
    WorkOrderProcessStage.objects.filter(
        deleted=False,
        stage_code__in=["MKT_APPROVED", "DESIGN_APPROVED", "MGMT_APPROVED"],
    ).exclude(
        track__workorder__status__in=[
            "App- MKT Dpt",
            "App- Design Dpt",
            "App-Management",
        ]
    ).update(deleted=True, deleted_at=now, is_applicable=False, updated_at=now)

    resync_all_jobwork_stages(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0027_prune_unselected_process_stages"),
    ]

    operations = [
        migrations.RunPython(drop_default_approval_stages, noop_reverse),
    ]
