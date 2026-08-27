from django.db import migrations, models
from django.utils import timezone

from workorder.process_constants import PROCESS_STAGE_CHOICES


def mechanical_test_only_with_ageing(apps, schema_editor):
    """
    Soft-delete Mechanical Test on tracks that do not require Ageing.
    Resync all tracks so sequence becomes: ... → Ageing → Mechanical Test.
    """
    from workorder.models import WorkOrderProcessStage, WorkOrderProcessTrack
    from workorder.process_tracking import resync_all_jobwork_stages

    now = timezone.now()
    tracks_without_ageing = WorkOrderProcessTrack.objects.filter(
        deleted=False, requires_ageing=False
    ).values_list("id", flat=True)
    WorkOrderProcessStage.objects.filter(
        deleted=False,
        stage_code="MECHANICAL_TEST",
        track_id__in=tracks_without_ageing,
    ).update(
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
        ("workorder", "0030_split_qc_into_three_inspections"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workorder",
            name="process_status",
            field=models.CharField(
                blank=True,
                choices=PROCESS_STAGE_CHOICES,
                db_index=True,
                default="WO_CREATED",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="workorderdetail",
            name="process_status",
            field=models.CharField(
                blank=True,
                choices=PROCESS_STAGE_CHOICES,
                db_index=True,
                default="WO_CREATED",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="workorderprocesstrack",
            name="current_stage",
            field=models.CharField(
                choices=PROCESS_STAGE_CHOICES,
                db_index=True,
                default="WO_CREATED",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="workorderprocessstage",
            name="stage_code",
            field=models.CharField(
                choices=PROCESS_STAGE_CHOICES, db_index=True, max_length=50
            ),
        ),
        migrations.RunPython(mechanical_test_only_with_ageing, noop_reverse),
    ]
