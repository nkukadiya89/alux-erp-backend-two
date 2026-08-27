"""
Workorder Process Tracking service.

Creates / advances item-level and planning-level process checklists.
Does NOT overwrite legacy WorkOrder.status / WorkOrderDetail.status used by
packing & dispatch — only maintains parallel `process_status` + checklist rows.

Jobwork stages (Engineering / Surface treatment / Laser / Thermal Break) are
inserted after Ageing when Surface Finish requires them, then:
  Vendor Out → Jobwork Invoice Linked → Return QC → Packing → Dispatch.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ageing_cycle.models import AgingCycle
from workorder.process_constants import (
    APPROVAL_STAGE_CODES,
    APPROVAL_STAGES_BY_WO_STATUS,
    JOBWORK_STAGE_CODES,
    LEGACY_DETAIL_STATUS_TO_PROCESS,
    LEGACY_WO_STATUS_TO_PROCESS,
    OPEN_STAGE_WO_STATUSES,
    PLANNING_CORE_AFTER_JOBWORK,
    PLANNING_CORE_BEFORE_JOBWORK,
    PLANNING_TRACK_STAGES,
    PROCESS_STAGE_LABELS,
    PROCESS_STAGE_ORDER,
    PROCESS_TO_LEGACY_DETAIL_STATUS,
    STAGE_COMPLETION_TRIGGERS,
)

logger = logging.getLogger(__name__)


def _stage_index(code: str) -> int:
    try:
        return PROCESS_STAGE_ORDER.index(code)
    except ValueError:
        return 0


def has_ageing_cycle_for(alloy_id, temper_id) -> bool:
    if not alloy_id or not temper_id:
        return False
    return AgingCycle.objects.filter(
        deleted=False, alloy_id=alloy_id, temper_id=temper_id
    ).exists()


def resolve_jobwork_stage_codes(workorder_detail) -> list[str]:
    """
    Build ordered jobwork subprocess codes from Surface Finish + detail flags.
    Empty list = Mill Finish / no vendor jobwork.
    """
    if not workorder_detail:
        return []

    names = set(
        workorder_detail.surface_finish.values_list("name", flat=True)
    )
    stages: list[str] = []

    if "Engineering" in names:
        sub = []
        if workorder_detail.cutting:
            sub.append("JW_CUTTING")
        if workorder_detail.machining:
            sub.append("JW_MACHINING")
        if workorder_detail.deburring:
            sub.append("JW_DEBURRING")
        stages.extend(sub or ["JW_ENGINEERING"])

    if "Surface treatment" in names:
        sub = []
        if workorder_detail.anodising:
            sub.append("JW_ANODISING")
        if workorder_detail.powder_coating:
            sub.append("JW_POWDER_COATING")
        if workorder_detail.pvdf:
            sub.append("JW_PVDF")
        stages.extend(sub or ["JW_SURFACE_TREATMENT"])

    if "Laser marking" in names:
        stages.append("JW_LASER_MARKING")

    if "Thermal Break" in names:
        stages.append("JW_THERMAL_BREAK")

    if stages:
        stages.extend(
            ["JW_VENDOR_OUT", "JW_INVOICE_LINKED", "JW_RETURN_QC"]
        )
    return stages


def resolve_approval_stage_codes(workorder_detail) -> list[str]:
    """
    Approval stages only when WO is on an approval path.
    Sales Order → Work Order create does NOT auto-include them (not yet approved).
    """
    wo = getattr(workorder_detail, "workorder", None)
    status = (wo.status if wo else None) or ""
    return list(APPROVAL_STAGES_BY_WO_STATUS.get(status, ()))


def include_open_stage(workorder_detail) -> bool:
    """Open stage only when WO status is Open (not default on SO → WO create)."""
    wo = getattr(workorder_detail, "workorder", None)
    status = (wo.status if wo else None) or ""
    return status in OPEN_STAGE_WO_STATUSES


def build_item_stage_pipeline(workorder_detail, requires_ageing: bool) -> list[tuple[str, bool]]:
    """
    Return only selected/applicable stages for an item track.
    - Marketing / Design / Management Approved: only if WO is in approval status
    - Open: only if WO status is Open (not default from Sales Order create)
    - Ageing: only when Ageing Cycle exists for Alloy+Temper
    - Mechanical Test: always after Dimension Inspection; after Ageing when Ageing applies
    - Jobwork: from Surface Finish selection on Sales Order / WO item
    """
    jobwork = resolve_jobwork_stage_codes(workorder_detail)
    has_jobwork = bool(jobwork)
    approvals = set(resolve_approval_stage_codes(workorder_detail))
    show_open = include_open_stage(workorder_detail)

    pipeline: list[tuple[str, bool]] = []
    for code in PROCESS_STAGE_ORDER:
        if code == "AGEING":
            if requires_ageing:
                pipeline.append((code, True))
            continue

        if code == "MECHANICAL_TEST":
            # Always in process: after Ageing if ageing required, else right after Dimension Inspection
            pipeline.append((code, True))
            continue

        if code in APPROVAL_STAGE_CODES:
            if code in approvals:
                pipeline.append((code, True))
            continue

        if code == "OPEN":
            if show_open:
                pipeline.append((code, True))
            continue

        if code in JOBWORK_STAGE_CODES:
            if code in jobwork:
                pipeline.append((code, True))
            continue

        if code == "FINAL_QC":
            if not has_jobwork:
                pipeline.append((code, True))
            continue

        if code in {
            "WO_CREATED",
            "IN_PLANNING",
            "IN_PRODUCTION",
            "ONLINE_INSPECTION",
            "DIMENSION_INSPECTION",
            "WAITING_FOR_PACKING",
            "PACKED",
            "DISPATCHED",
            "CLOSED",
        }:
            pipeline.append((code, True))

    return pipeline


def build_planning_stage_pipeline(workorder_detail, requires_ageing: bool) -> list[tuple[str, bool]]:
    """Only selected/applicable stages for a planning-no track."""
    jobwork = resolve_jobwork_stage_codes(workorder_detail)
    has_jobwork = bool(jobwork)
    pipeline: list[tuple[str, bool]] = []

    for code in PLANNING_CORE_BEFORE_JOBWORK:
        if code == "AGEING":
            if requires_ageing:
                pipeline.append((code, True))
        elif code == "MECHANICAL_TEST":
            pipeline.append((code, True))
        else:
            pipeline.append((code, True))

    for code in PROCESS_STAGE_ORDER:
        if code in JOBWORK_STAGE_CODES and code in jobwork:
            pipeline.append((code, True))

    for code in PLANNING_CORE_AFTER_JOBWORK:
        if code == "FINAL_QC":
            if not has_jobwork:
                pipeline.append((code, True))
        else:
            pipeline.append((code, True))

    return pipeline


@transaction.atomic
def ensure_item_process_track(workorder_detail, user=None, mark_created=True):
    """Create item-level process track + stage checkboxes if missing."""
    from workorder.models import WorkOrderProcessTrack

    if not workorder_detail or workorder_detail.deleted:
        return None

    track = (
        WorkOrderProcessTrack.objects.select_for_update()
        .filter(
            workorder_detail_id=workorder_detail.id,
            scope="ITEM",
            planning__isnull=True,
            deleted=False,
        )
        .first()
    )

    requires_ageing = has_ageing_cycle_for(
        getattr(workorder_detail, "alloy_id", None),
        getattr(workorder_detail, "temper_id", None),
    )
    pipeline = build_item_stage_pipeline(workorder_detail, requires_ageing)
    has_jobwork = any(
        code in JOBWORK_STAGE_CODES and applicable for code, applicable in pipeline
    )

    if not track:
        track = WorkOrderProcessTrack.objects.create(
            workorder_id=workorder_detail.workorder_id,
            workorder_detail=workorder_detail,
            planning=None,
            scope="ITEM",
            current_stage="WO_CREATED",
            requires_ageing=requires_ageing,
            created_by=user,
        )
        _create_stage_rows_from_pipeline(track, pipeline, user=user)
        if mark_created:
            _complete_stages_upto(track, "WO_CREATED", user=user)
        _sync_detail_process_status(workorder_detail, track.current_stage, user=user)
        _refresh_workorder_process_status(workorder_detail.workorder_id, user=user)
    else:
        if track.requires_ageing != requires_ageing:
            track.requires_ageing = requires_ageing
            track.save(update_fields=["requires_ageing", "updated_at"])
        sync_track_stages_from_pipeline(track, pipeline, user=user)

    # Store hint on track via remarks not needed; requires_ageing already set
    _ = has_jobwork
    return track


@transaction.atomic
def ensure_planning_process_track(planning, user=None):
    """Create planning-no process track when planning exists."""
    from workorder.models import WorkOrderProcessTrack

    if not planning or getattr(planning, "deleted", False):
        return None
    if not planning.workorder_detail_id:
        return None

    detail = planning.workorder_detail
    ensure_item_process_track(detail, user=user)

    track = (
        WorkOrderProcessTrack.objects.select_for_update()
        .filter(
            planning_id=planning.id,
            scope="PLANNING",
            deleted=False,
        )
        .first()
    )

    requires_ageing = has_ageing_cycle_for(
        getattr(detail, "alloy_id", None),
        getattr(detail, "temper_id", None),
    )
    if getattr(planning, "ageing_id", None):
        requires_ageing = True

    pipeline = build_planning_stage_pipeline(detail, requires_ageing)

    if not track:
        track = WorkOrderProcessTrack.objects.create(
            workorder_id=planning.workorder_id or detail.workorder_id,
            workorder_detail=detail,
            planning=planning,
            scope="PLANNING",
            current_stage="IN_PLANNING",
            requires_ageing=requires_ageing,
            created_by=user,
        )
        _create_stage_rows_from_pipeline(track, pipeline, user=user)
        _complete_stages_upto(track, "IN_PLANNING", user=user)
    else:
        if track.requires_ageing != requires_ageing:
            track.requires_ageing = requires_ageing
            track.save(update_fields=["requires_ageing", "updated_at"])
        sync_track_stages_from_pipeline(track, pipeline, user=user)

    return track


def _create_stage_rows_from_pipeline(track, pipeline, user=None):
    """Persist only selected (applicable) stages — skip non-selected Jobwork rows."""
    from workorder.models import WorkOrderProcessStage

    rows = []
    seq = 0
    for code, applicable in pipeline:
        if not applicable:
            continue
        rows.append(
            WorkOrderProcessStage(
                track=track,
                stage_code=code,
                stage_label=PROCESS_STAGE_LABELS.get(code, code),
                sequence=seq,
                is_applicable=True,
                is_completed=False,
                created_by=user,
            )
        )
        seq += 1
    if rows:
        WorkOrderProcessStage.objects.bulk_create(rows)


@transaction.atomic
def sync_track_stages_from_pipeline(track, pipeline, user=None):
    """
    Keep stage rows in sync with Sales Order / WO Surface Finish selection.
    - Create missing selected stages
    - Soft-delete stages that are no longer selected (reduces data load)
    """
    from workorder.models import WorkOrderProcessStage

    desired = [code for code, applicable in pipeline if applicable]
    desired_codes = set(desired)

    existing = {
        s.stage_code: s
        for s in track.stages.filter(deleted=False)
    }

    now = timezone.now()

    # Soft-delete processes not selected on Sales Order / item
    for code, stage in list(existing.items()):
        if code not in desired_codes:
            stage.deleted = True
            stage.deleted_at = now
            stage.deleted_by = user
            stage.is_applicable = False
            stage.save(
                update_fields=[
                    "deleted",
                    "deleted_at",
                    "deleted_by",
                    "is_applicable",
                    "updated_at",
                ]
            )
            existing.pop(code, None)

    for idx, code in enumerate(desired):
        stage = existing.get(code)
        if not stage:
            WorkOrderProcessStage.objects.create(
                track=track,
                stage_code=code,
                stage_label=PROCESS_STAGE_LABELS.get(code, code),
                sequence=idx,
                is_applicable=True,
                is_completed=False,
                created_by=user,
            )
            continue

        update_fields = []
        if stage.sequence != idx:
            stage.sequence = idx
            update_fields.append("sequence")
        if not stage.is_applicable:
            stage.is_applicable = True
            update_fields.append("is_applicable")
        if update_fields:
            stage.updated_by = user
            update_fields.extend(["updated_by", "updated_at"])
            stage.save(update_fields=list(dict.fromkeys(update_fields)))

    return track


@transaction.atomic
def sync_jobwork_stages_for_detail(workorder_detail, user=None):
    """Re-evaluate jobwork applicability after SO/WO surface finish edits."""
    if not workorder_detail:
        return
    track = ensure_item_process_track(workorder_detail, user=user, mark_created=True)
    if not track:
        return
    requires_ageing = has_ageing_cycle_for(
        workorder_detail.alloy_id, workorder_detail.temper_id
    )
    pipeline = build_item_stage_pipeline(workorder_detail, requires_ageing)
    sync_track_stages_from_pipeline(track, pipeline, user=user)

    from planning.models import Planning
    from workorder.models import WorkOrderProcessTrack

    for planning in Planning.objects.filter(
        workorder_detail_id=workorder_detail.id, deleted=False
    ):
        plan_track = WorkOrderProcessTrack.objects.filter(
            planning_id=planning.id, scope="PLANNING", deleted=False
        ).first()
        if plan_track:
            plan_pipeline = build_planning_stage_pipeline(
                workorder_detail,
                requires_ageing or bool(planning.ageing_id),
            )
            sync_track_stages_from_pipeline(plan_track, plan_pipeline, user=user)


def _complete_stages_upto(track, target_stage: str, user=None, remarks=None):
    """Mark all applicable stages up to and including target as completed."""
    target_idx = _stage_index(target_stage)
    now = timezone.now()
    stages = list(
        track.stages.filter(deleted=False, is_applicable=True).order_by("sequence")
    )
    for stage in stages:
        if _stage_index(stage.stage_code) <= target_idx and not stage.is_completed:
            stage.is_completed = True
            stage.completed_at = now
            stage.completed_by = user
            if remarks:
                stage.remarks = remarks
            stage.save(
                update_fields=[
                    "is_completed",
                    "completed_at",
                    "completed_by",
                    "remarks",
                    "updated_at",
                ]
            )

    stages = list(
        track.stages.filter(deleted=False, is_applicable=True).order_by("sequence")
    )
    furthest = stages[0].stage_code if stages else "WO_CREATED"
    for s in stages:
        if s.is_completed:
            furthest = s.stage_code
        else:
            break

    if track.current_stage != furthest:
        track.current_stage = furthest
        track.updated_by = user
        track.save(update_fields=["current_stage", "updated_by", "updated_at"])

    return track


@transaction.atomic
def advance_process(
    *,
    workorder_detail=None,
    planning=None,
    stage: str,
    user=None,
    remarks: Optional[str] = None,
    sync_legacy_detail_status: bool = False,
):
    """
    Advance item track (and planning track if planning provided) to `stage`.
    Completes all prior applicable stages (checkbox list).
    """
    if stage not in PROCESS_STAGE_LABELS:
        logger.warning("Unknown process stage: %s", stage)
        return None

    detail = workorder_detail
    if planning is not None and detail is None:
        detail = planning.workorder_detail

    if detail is None:
        return None

    item_track = ensure_item_process_track(detail, user=user)

    if stage in PROCESS_STAGE_ORDER:
        if _stage_index(stage) >= _stage_index(item_track.current_stage):
            _complete_stages_upto(item_track, stage, user=user, remarks=remarks)
            _sync_detail_process_status(
                detail,
                item_track.current_stage,
                user=user,
                sync_legacy=sync_legacy_detail_status,
            )

    if planning is not None:
        plan_track = ensure_planning_process_track(planning, user=user)
        if plan_track and stage in PLANNING_TRACK_STAGES:
            if _stage_index(stage) >= _stage_index(plan_track.current_stage):
                _complete_stages_upto(plan_track, stage, user=user, remarks=remarks)

    _refresh_workorder_process_status(detail.workorder_id, user=user)
    return item_track


def _sync_detail_process_status(
    detail, process_status: str, user=None, sync_legacy: bool = False
):
    update_fields = []
    if detail.process_status != process_status:
        detail.process_status = process_status
        update_fields.append("process_status")

    if sync_legacy:
        legacy = PROCESS_TO_LEGACY_DETAIL_STATUS.get(process_status)
        protected = {"Packed", "Dispatched"}
        if legacy and detail.status not in protected and detail.status != legacy:
            detail.status = legacy
            update_fields.append("status")

    if update_fields:
        detail.updated_by = user
        update_fields.extend(["updated_by", "updated_at"])
        detail.save(update_fields=list(dict.fromkeys(update_fields)))


def _refresh_workorder_process_status(workorder_id, user=None):
    from workorder.models import WorkOrder, WorkOrderDetail

    if not workorder_id:
        return

    statuses = list(
        WorkOrderDetail.objects.filter(
            workorder_id=workorder_id, deleted=False
        ).values_list("process_status", flat=True)
    )
    if not statuses:
        return

    least = min(
        (s or "WO_CREATED" for s in statuses),
        key=_stage_index,
    )
    WorkOrder.objects.filter(id=workorder_id, deleted=False).exclude(
        process_status=least
    ).update(
        process_status=least,
        updated_by=user,
        updated_at=timezone.now(),
    )


@transaction.atomic
def bootstrap_tracks_for_workorder(workorder, user=None):
    from workorder.models import WorkOrderDetail

    details = WorkOrderDetail.objects.filter(workorder=workorder, deleted=False)
    for detail in details:
        ensure_item_process_track(detail, user=user, mark_created=True)
        sync_jobwork_stages_for_detail(detail, user=user)
    _refresh_workorder_process_status(workorder.id, user=user)


@transaction.atomic
def resync_all_jobwork_stages(user=None, batch_size: int = 200):
    """Refresh jobwork applicability on all existing tracks (safe)."""
    from workorder.models import WorkOrderDetail

    ids = list(
        WorkOrderDetail.objects.filter(deleted=False)
        .order_by("id")
        .values_list("id", flat=True)
    )
    for start in range(0, len(ids), batch_size):
        for detail in WorkOrderDetail.objects.filter(
            id__in=ids[start : start + batch_size]
        ).prefetch_related("surface_finish"):
            sync_jobwork_stages_for_detail(detail, user=user)
    return len(ids)


@transaction.atomic
def backfill_existing_workorders(user=None, batch_size: int = 200):
    from planning.models import Planning
    from workorder.models import WorkOrder, WorkOrderDetail

    wo_ids = list(
        WorkOrder.objects.filter(deleted=False).order_by("id").values_list("id", flat=True)
    )
    for start in range(0, len(wo_ids), batch_size):
        chunk = wo_ids[start : start + batch_size]
        details = (
            WorkOrderDetail.objects.filter(workorder_id__in=chunk, deleted=False)
            .select_related("workorder", "alloy", "temper")
            .prefetch_related("surface_finish")
        )
        for detail in details:
            track = ensure_item_process_track(detail, user=user, mark_created=False)
            sync_jobwork_stages_for_detail(detail, user=user)
            inferred = _infer_stage_for_detail(detail)
            _complete_stages_upto(track, inferred, user=user, remarks="Backfill")
            if detail.process_status != track.current_stage:
                detail.process_status = track.current_stage
                detail.save(update_fields=["process_status", "updated_at"])

            for planning in Planning.objects.filter(
                workorder_detail_id=detail.id, deleted=False
            ):
                plan_track = ensure_planning_process_track(planning, user=user)
                plan_inferred = _infer_stage_for_planning(planning, detail)
                if plan_track:
                    _complete_stages_upto(
                        plan_track, plan_inferred, user=user, remarks="Backfill"
                    )

        for wo_id in chunk:
            _refresh_workorder_process_status(wo_id, user=user)

    return len(wo_ids)


def _infer_stage_for_detail(detail) -> str:
    from planning.models import Planning
    from production.models import Production

    legacy = LEGACY_DETAIL_STATUS_TO_PROCESS.get(detail.status or "", "WO_CREATED")

    if (detail.dispatched_weight or 0) > 0 or detail.status == "Dispatched":
        return "DISPATCHED"
    if (detail.packed_weight or 0) > 0 or detail.status == "Packed":
        return "PACKED"

    has_prod = Production.objects.filter(
        workorder_id=detail.workorder_id,
        deleted=False,
        status="SUBMITTED",
        planning__workorder_detail_id=detail.id,
    ).exists()
    if has_prod:
        from aging.models import AgeingBatchDetail

        aged = AgeingBatchDetail.objects.filter(
            deleted=False,
            production_no__planning__workorder_detail_id=detail.id,
            production_no__deleted=False,
        ).exists()
        if aged:
            return "AGEING"
        return "IN_PRODUCTION"

    has_plan = Planning.objects.filter(
        workorder_detail_id=detail.id, deleted=False
    ).exists()
    if has_plan or detail.status == "In-Planning" or detail.is_palnning:
        return "IN_PLANNING"

    if detail.workorder and detail.workorder.status == "Closed":
        return "CLOSED"

    wo_legacy = LEGACY_WO_STATUS_TO_PROCESS.get(
        (detail.workorder.status if detail.workorder else "") or "", ""
    )
    candidates = [legacy, wo_legacy or "WO_CREATED"]
    return max(candidates, key=_stage_index)


def _infer_stage_for_planning(planning, detail) -> str:
    from production.models import Production

    if detail.status == "Dispatched" or (detail.dispatched_weight or 0) > 0:
        return "DISPATCHED"
    if detail.status == "Packed" or (detail.packed_weight or 0) > 0:
        return "PACKED"

    prod = Production.objects.filter(
        planning_id=planning.id, deleted=False, status="SUBMITTED"
    ).exists()
    if prod:
        from aging.models import AgeingBatchDetail

        if AgeingBatchDetail.objects.filter(
            deleted=False, production_no__planning_id=planning.id
        ).exists():
            return "AGEING"
        return "IN_PRODUCTION"

    return "IN_PLANNING"


def get_completion_rules():
    return [
        {"code": code, "label": PROCESS_STAGE_LABELS[code], "completed_when": when}
        for code, when in STAGE_COMPLETION_TRIGGERS.items()
    ]
