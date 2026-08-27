from django.db import transaction
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from workorder.models import WorkOrder, WorkOrderProcessStage, WorkOrderProcessTrack
from workorder.process_constants import (
    PROCESS_STAGE_CHOICES,
    PROCESS_STAGE_LABELS,
)
from workorder.process_serializers import (
    WorkOrderProcessTrackingListSerializer,
    WorkOrderProcessTrackSerializer,
)
from workorder.process_tracking import (
    advance_process,
    ensure_item_process_track,
    get_completion_rules,
)


class WorkOrderProcessTrackingViewSet(BaseModelViewSet, ArchiveMixin):
    """
    Read/update API for Workorder Process Tracking screen.
    List is workorder-wise; retrieve expands item + planning tracks with checkboxes.
    """

    queryset = WorkOrder.objects.filter(deleted=False).select_related("bill_to")
    serializer_class = WorkOrderProcessTrackingListSerializer
    list_serializer_class = WorkOrderProcessTrackingListSerializer
    search_fields = [
        "order_no",
        "bill_to__customer_name",
        "bill_to__code",
        "process_status",
        "status",
        "process_tracks__planning__planning_no",
        "process_tracks__workorder_detail__die_profile__die_number",
        "process_tracks__workorder_detail__alloy__alloy_code",
    ]
    ordering_fields = ["id", "order_no", "order_date", "process_status", "created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset().filter(deleted=False).order_by("-id")
        # Avoid duplicate WO rows when searching across process_tracks
        qs = qs.distinct()
        item_tracks = Prefetch(
            "process_tracks",
            queryset=WorkOrderProcessTrack.objects.filter(
                deleted=False, scope="ITEM", is_active=True
            )
            .select_related(
                "workorder_detail",
                "workorder_detail__die_profile",
                "workorder_detail__alloy",
                "workorder_detail__temper",
                "planning",
            )
            .prefetch_related(
                Prefetch(
                    "stages",
                    queryset=WorkOrderProcessStage.objects.filter(
                        deleted=False, is_applicable=True
                    )
                    .select_related("completed_by")
                    .order_by("sequence"),
                )
            )
            .order_by("workorder_detail_id"),
            to_attr="prefetched_item_tracks",
        )
        return qs.prefetch_related(item_tracks)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = WorkOrderProcessTrackingListSerializer(
            page if page is not None else queryset, many=True
        )
        if page is not None:
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        workorder = self.get_object()
        # Re-sync stages from current Surface Finish / flags (in-house vs vendor rules).
        for detail in workorder.workorder_detail_workorder.filter(deleted=False):
            ensure_item_process_track(detail, user=request.user)
            # Sync Packed / Dispatched from live qty vs WO order + tolerance
            try:
                from utils.packing_tolerance import is_quantity_fulfilled

                detail.refresh_from_db()
                packed_pcs = (detail.packed_pieces or 0) + (detail.dispatched_pieces or 0)
                packed_wt = (detail.packed_weight or 0) + (detail.dispatched_weight or 0)
                if is_quantity_fulfilled(packed_pcs, packed_wt, detail):
                    advance_process(
                        workorder_detail=detail,
                        stage="PACKED",
                        user=request.user,
                        remarks="Synced from packed qty vs WO tolerance",
                    )
                if is_quantity_fulfilled(
                    detail.dispatched_pieces or 0,
                    detail.dispatched_weight or 0,
                    detail,
                ):
                    advance_process(
                        workorder_detail=detail,
                        stage="DISPATCHED",
                        user=request.user,
                        remarks="Synced from dispatched qty vs WO tolerance",
                    )
            except Exception:
                pass


        tracks = (
            WorkOrderProcessTrack.objects.filter(
                workorder=workorder, deleted=False, is_active=True
            )
            .select_related(
                "workorder",
                "workorder__bill_to",
                "workorder_detail",
                "workorder_detail__die_profile",
                "workorder_detail__alloy",
                "workorder_detail__temper",
                "planning",
            )
            .prefetch_related(
                Prefetch(
                    "stages",
                    queryset=WorkOrderProcessStage.objects.filter(
                        deleted=False, is_applicable=True
                    )
                    .select_related("completed_by")
                    .order_by("sequence"),
                )
            )
            .order_by("scope", "workorder_detail_id", "id")
        )
        return Response(
            {
                "success": True,
                "data": {
                    "workorder": {
                        "id": workorder.id,
                        "order_no": workorder.order_no,
                        "order_date": workorder.order_date,
                        "process_status": workorder.process_status,
                        "process_status_label": PROCESS_STAGE_LABELS.get(
                            workorder.process_status or "", workorder.process_status
                        ),
                        "legacy_status": workorder.status,
                        "customer_name": getattr(
                            workorder.bill_to, "customer_name", None
                        ),
                        "customer_code": getattr(workorder.bill_to, "code", None),
                    },
                    "tracks": WorkOrderProcessTrackSerializer(tracks, many=True).data,
                    "stages_master": [
                        {"code": c, "label": l} for c, l in PROCESS_STAGE_CHOICES
                    ],
                    "completion_rules": get_completion_rules(),
                    "flow_note": (
                        "After Planning → Production → Online Inspection → "
                        "Dimension Inspection: if Ageing Cycle exists for Alloy+Temper, "
                        "Ageing then Mechanical Test; otherwise Mechanical Test directly "
                        "after Dimension Inspection. Then jobwork stages follow Surface Finish: "
                        "Engineering → Cutting can be in-house (no vendor steps). "
                        "Machining / Surface treatment (Anodising etc.) / Laser / Thermal / "
                        "Out Source use vendor path: Sent to Third Party Vendor → "
                        "Jobwork Invoice Linked → Return QC → Packing → Dispatch. "
                        "Mill Finish skips jobwork and uses Final QC before packing."
                    ),
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="stages")
    def stages(self, request):
        return Response(
            {
                "success": True,
                "data": {
                    "stages": [
                        {"code": c, "label": l} for c, l in PROCESS_STAGE_CHOICES
                    ],
                    "completion_rules": get_completion_rules(),
                },
            }
        )

    @action(detail=True, methods=["post"], url_path="advance")
    @transaction.atomic
    def advance(self, request, pk=None):
        """
        Manual advance / checkbox complete.
        body: { workorder_detail_id, planning_id?, stage, remarks? }
        """
        workorder = self.get_object()
        stage = request.data.get("stage")
        detail_id = request.data.get("workorder_detail_id")
        planning_id = request.data.get("planning_id")
        remarks = request.data.get("remarks")

        if not stage or not detail_id:
            return Response(
                {
                    "success": False,
                    "message": "stage and workorder_detail_id are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        detail = workorder.workorder_detail_workorder.filter(
            id=detail_id, deleted=False
        ).first()
        if not detail:
            return Response(
                {"success": False, "message": "WorkOrder detail not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        planning = None
        if planning_id:
            from planning.models import Planning

            planning = Planning.objects.filter(
                id=planning_id,
                workorder_detail_id=detail.id,
                deleted=False,
            ).first()

        track = advance_process(
            workorder_detail=detail,
            planning=planning,
            stage=stage,
            user=request.user,
            remarks=remarks,
            sync_legacy_detail_status=False,
        )
        ensure_item_process_track(detail, user=request.user)
        return Response(
            {
                "success": True,
                "message": f"Advanced to {PROCESS_STAGE_LABELS.get(stage, stage)}",
                "data": WorkOrderProcessTrackSerializer(track).data if track else None,
            }
        )
