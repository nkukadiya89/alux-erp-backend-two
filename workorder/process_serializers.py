from rest_framework import serializers

from workorder.models import WorkOrderProcessStage, WorkOrderProcessTrack
from workorder.process_constants import PROCESS_STAGE_LABELS, STAGE_COMPLETION_TRIGGERS


class WorkOrderProcessStageSerializer(serializers.ModelSerializer):
    completed_when = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrderProcessStage
        fields = [
            "id",
            "stage_code",
            "stage_label",
            "sequence",
            "is_applicable",
            "is_completed",
            "status",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "remarks",
            "completed_when",
        ]

    def get_completed_when(self, obj):
        return STAGE_COMPLETION_TRIGGERS.get(obj.stage_code, "")

    def get_completed_by_name(self, obj):
        user = obj.completed_by
        if not user:
            return None
        full = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
        return full or getattr(user, "username", None) or str(user.id)

    def get_status(self, obj):
        if not obj.is_applicable:
            return "Skipped"
        if obj.is_completed:
            return "Completed"
        return "Pending"


class WorkOrderProcessTrackSerializer(serializers.ModelSerializer):
    stages = serializers.SerializerMethodField()
    current_stage_label = serializers.SerializerMethodField()
    next_pending_stage = serializers.SerializerMethodField()
    next_pending_label = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    total_applicable = serializers.SerializerMethodField()
    planning_no = serializers.CharField(
        source="planning.planning_no", read_only=True, default=None
    )
    workorder_no = serializers.CharField(
        source="workorder.order_no", read_only=True, default=None
    )
    profile = serializers.CharField(
        source="workorder_detail.die_profile.die_number", read_only=True, default=None
    )
    alloy_code = serializers.CharField(
        source="workorder_detail.alloy.alloy_code", read_only=True, default=None
    )
    temper_code = serializers.CharField(
        source="workorder_detail.temper.temper_code_new", read_only=True, default=None
    )
    length = serializers.IntegerField(
        source="workorder_detail.length", read_only=True, default=None
    )
    customer_name = serializers.CharField(
        source="workorder.bill_to.customer_name", read_only=True, default=None
    )
    customer_code = serializers.CharField(
        source="workorder.bill_to.code", read_only=True, default=None
    )

    class Meta:
        model = WorkOrderProcessTrack
        fields = [
            "id",
            "workorder",
            "workorder_no",
            "workorder_detail",
            "planning",
            "planning_no",
            "scope",
            "current_stage",
            "current_stage_label",
            "next_pending_stage",
            "next_pending_label",
            "completed_count",
            "pending_count",
            "total_applicable",
            "requires_ageing",
            "is_active",
            "profile",
            "alloy_code",
            "temper_code",
            "length",
            "customer_name",
            "customer_code",
            "stages",
            "created_at",
            "updated_at",
        ]

    def get_current_stage_label(self, obj):
        return PROCESS_STAGE_LABELS.get(obj.current_stage, obj.current_stage)

    def get_stages(self, obj):
        # Only selected / applicable processes (Sales Order Surface Finish driven)
        stages = getattr(obj, "_prefetched_objects_cache", {}).get("stages")
        if stages is None:
            stages = obj.stages.filter(deleted=False, is_applicable=True).order_by(
                "sequence"
            )
        else:
            stages = [
                s
                for s in stages
                if not getattr(s, "deleted", False) and getattr(s, "is_applicable", True)
            ]
            stages = sorted(stages, key=lambda s: s.sequence or 0)
        return WorkOrderProcessStageSerializer(stages, many=True).data

    def _applicable_stages(self, obj):
        stages = getattr(obj, "_prefetched_objects_cache", {}).get("stages")
        if stages is not None:
            return sorted(
                [s for s in stages if not s.deleted and s.is_applicable],
                key=lambda s: s.sequence or 0,
            )
        return list(
            obj.stages.filter(deleted=False, is_applicable=True).order_by("sequence")
        )

    def _next_pending(self, obj):
        for stage in self._applicable_stages(obj):
            if not stage.is_completed:
                return stage
        return None

    def get_next_pending_stage(self, obj):
        stage = self._next_pending(obj)
        return stage.stage_code if stage else None

    def get_next_pending_label(self, obj):
        stage = self._next_pending(obj)
        if stage:
            return stage.stage_label or PROCESS_STAGE_LABELS.get(stage.stage_code)
        return "All processes completed"

    def get_completed_count(self, obj):
        return sum(1 for s in self._applicable_stages(obj) if s.is_completed)

    def get_pending_count(self, obj):
        return sum(1 for s in self._applicable_stages(obj) if not s.is_completed)

    def get_total_applicable(self, obj):
        return len(self._applicable_stages(obj))


class WorkOrderProcessTrackingListSerializer(serializers.Serializer):
    """Flattened list row: one workorder with nested item tracks."""

    id = serializers.IntegerField()
    order_no = serializers.CharField()
    order_date = serializers.DateField(allow_null=True)
    process_status = serializers.CharField(allow_null=True)
    process_status_label = serializers.SerializerMethodField()
    legacy_status = serializers.CharField(source="status", allow_null=True)
    customer_name = serializers.CharField(
        source="bill_to.customer_name", allow_null=True, default=None
    )
    customer_code = serializers.CharField(
        source="bill_to.code", allow_null=True, default=None
    )
    item_count = serializers.SerializerMethodField()
    next_pending_label = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    def get_process_status_label(self, obj):
        return PROCESS_STAGE_LABELS.get(obj.process_status or "", obj.process_status)

    def get_item_count(self, obj):
        return len(getattr(obj, "prefetched_item_tracks", []) or [])

    def get_next_pending_label(self, obj):
        tracks = getattr(obj, "prefetched_item_tracks", None) or []
        labels = []
        for track in tracks:
            cached = getattr(track, "_prefetched_objects_cache", {}).get("stages")
            stages = cached if cached is not None else list(track.stages.all())
            stages = sorted(
                [
                    s
                    for s in stages
                    if getattr(s, "is_applicable", False)
                    and not getattr(s, "deleted", False)
                ],
                key=lambda s: s.sequence or 0,
            )
            pending = next((s for s in stages if not s.is_completed), None)
            if pending:
                labels.append(pending.stage_label)
        if not labels:
            return "All processes completed" if tracks else "-"
        seen = set()
        unique = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique.append(label)
        return ", ".join(unique[:3]) + ("…" if len(unique) > 3 else "")

    def get_items(self, obj):
        tracks = getattr(obj, "prefetched_item_tracks", None)
        if tracks is None:
            tracks = obj.process_tracks.filter(
                deleted=False, scope="ITEM", is_active=True
            ).prefetch_related("stages")
        return WorkOrderProcessTrackSerializer(tracks, many=True).data
