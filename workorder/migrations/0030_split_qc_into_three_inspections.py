from django.db import migrations, models
from django.utils import timezone

from workorder.process_constants import PROCESS_STAGE_CHOICES


NEW_QC_STAGES = (
    ("ONLINE_INSPECTION", "Online Inspection"),
    ("DIMENSION_INSPECTION", "Dimension Inspection"),
    ("MECHANICAL_TEST", "Mechanical Test"),
)


def split_qc_inspection_stages(apps, schema_editor):
    """
    Replace legacy QC_INSPECTION rows with Online / Dimension / Mechanical Test.
    If QC was already completed, mark all three as completed.
    """
    WorkOrderProcessStage = apps.get_model("workorder", "WorkOrderProcessStage")
    WorkOrderProcessTrack = apps.get_model("workorder", "WorkOrderProcessTrack")
    WorkOrder = apps.get_model("workorder", "WorkOrder")
    WorkOrderDetail = apps.get_model("workorder", "WorkOrderDetail")

    now = timezone.now()
    new_codes = [c for c, _ in NEW_QC_STAGES]
    labels = dict(NEW_QC_STAGES)

    qc_stages = list(
        WorkOrderProcessStage.objects.filter(
            deleted=False, stage_code="QC_INSPECTION"
        ).select_related("track")
    )

    for qc in qc_stages:
        track = qc.track
        base_seq = qc.sequence or 0
        was_completed = bool(qc.is_completed)

        qc.deleted = True
        qc.deleted_at = now
        qc.is_applicable = False
        qc.save(
            update_fields=["deleted", "deleted_at", "is_applicable", "updated_at"]
        )

        # Shift later stages to make room for 3 QC stages (net +2 sequences)
        WorkOrderProcessStage.objects.filter(
            track=track, deleted=False, sequence__gt=base_seq
        ).update(sequence=models.F("sequence") + 2)

        for i, code in enumerate(new_codes):
            exists = WorkOrderProcessStage.objects.filter(
                track=track, stage_code=code, deleted=False
            ).exists()
            if exists:
                continue
            WorkOrderProcessStage.objects.create(
                track=track,
                stage_code=code,
                stage_label=labels[code],
                sequence=base_seq + i,
                is_applicable=True,
                is_completed=was_completed,
                completed_at=qc.completed_at if was_completed else None,
                completed_by_id=qc.completed_by_id if was_completed else None,
                remarks="Migrated from QC Inspection" if was_completed else None,
                created_at=now,
            )

        if track.current_stage == "QC_INSPECTION":
            track.current_stage = (
                "MECHANICAL_TEST" if was_completed else "ONLINE_INSPECTION"
            )
            track.save(update_fields=["current_stage", "updated_at"])

    WorkOrder.objects.filter(process_status="QC_INSPECTION").update(
        process_status="ONLINE_INSPECTION", updated_at=now
    )
    WorkOrderDetail.objects.filter(process_status="QC_INSPECTION").update(
        process_status="ONLINE_INSPECTION", updated_at=now
    )

    # Resync remaining tracks that never had QC_INSPECTION row yet
    from workorder.process_tracking import resync_all_jobwork_stages

    resync_all_jobwork_stages(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0029_drop_default_open_stage"),
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
        migrations.RunPython(split_qc_inspection_stages, noop_reverse),
    ]
