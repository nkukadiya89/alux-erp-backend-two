from rest_framework import serializers
from common.serializers import BaseModelSerializer
from die.sort_serializers import DieSortSerializers
from die_requisition.serializers import (
    DieRequisitionSerializer,
)
from ageing_cycle.serializers import AgingCycleListSerializer
from planning.models import Planning
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from workorder.serializers import WorkOrderDetailSerializers
from workorder.sort_serializers import WorkOrderListSerializer
from django.utils import timezone


def _press_payload(press):
    if not press:
        return None
    return {
        "id": press.id,
        "name": press.name,
        "code": getattr(press, "code", None),
        "billet_length_min": getattr(press, "billet_length_min", None),
        "billet_length_max": getattr(press, "billet_length_max", None),
        "billet_wt_factor": getattr(press, "billet_wt_factor", None),
    }


def _die_tool_payload(tool):
    if not tool:
        return None  
    return {
        "id": tool.id,
        "tool_number": tool.tool_number,
        "die_cavity": tool.die_cavity,
        "actual_kg": tool.actual_kg,
        "drawing_no": getattr(tool, "drawing_no", None),
        "die_oblique_number": getattr(tool, "die_oblique_number", None),
        "eligible_for_press": _press_payload(getattr(tool, "eligible_for_press", None)),
    }


def _alloy_payload(alloy):
    if not alloy:
        return None
    standard = getattr(alloy, "standard", None)
    return {
        "id": alloy.id,
        "alloy_code": alloy.alloy_code,
        "color_code": getattr(alloy, "color_code", None),
        "standard": {"name": standard.name} if standard else None,
    }


def _temper_payload(temper):
    if not temper:
        return None
    standard = getattr(temper, "standard", None)
    section_type = getattr(temper, "section_type", None)
    return {
        "id": temper.id,
        "temper_code_new": temper.temper_code_new,
        "standard": {"name": standard.name} if standard else None,
        "section_type": {"name": section_type.name} if section_type else None,
    }


class PlanningListSerializer(BaseModelSerializer):
    customer_name = serializers.CharField(source="workorder.bill_to.code", read_only=True)
    die_requisition = serializers.CharField(source="die_requisition.requisition_no", read_only=True)
    workorder_no = serializers.CharField(source="workorder.order_no", read_only=True)
    workorder_date = serializers.DateField(source="workorder.order_date", read_only=True)
    profile_image = serializers.CharField(source="profile_no.die_diagram", read_only=True)
    profile = serializers.CharField(source="profile_no.die_number", read_only=True)
    press = serializers.CharField(source="die_requisition_detail.press.name", read_only=True, allow_null=True, default=None)
    alloy = AlloySortSerializers(source="workorder_detail.alloy", read_only=True)
    temper = TemperSortSerializers(source="workorder_detail.temper", read_only=True)
    length = serializers.CharField(source="workorder_detail.length", read_only=True)
    standard_wt_kg_p_mt = serializers.CharField(source="profile_no.wt_kg_p_mt", read_only=True)
    ageing = serializers.CharField(source="ageing.cycle_name", read_only=True)
    last_wt_kg_p_mt = serializers.SerializerMethodField()
    max_wt_kg_p_mt = serializers.SerializerMethodField()
    die_tool_assigned_in_requisition = serializers.SerializerMethodField()
    die_tool_selected_in_planning = serializers.SerializerMethodField()
    die_tool_requisition_status = serializers.SerializerMethodField()
    die_tool_planning_status = serializers.SerializerMethodField()
    produced_pcs = serializers.SerializerMethodField()
    remaining_pcs = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Planning
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "planning_no",
            "planning_date",
            "created_at",
            "customer_name",
            "profile",
            "alloy",
            "temper",
            "length",
            "profile_image",
            "standard_wt_kg_p_mt",
            "last_wt_kg_p_mt",
            "max_wt_kg_p_mt",
            "die_tool_assigned_in_requisition",
            "die_tool_selected_in_planning",
            "die_tool_requisition_status",
            "die_tool_planning_status",
            "die_requisition_detail",
            "press",
            "die_requisition",
            "quenching_type",
            "workorder_no",
            "workorder_date",
            "ageing",
            "status",
            "plan_pcs",
            "plan_qty",
            "produced_pcs",
            "remaining_pcs",
        ]

    def _requisition_tool_details(self, instance):
        if not instance.die_requisition_id:
            return []
        # Prefetched as die_requisition.die_requisition (related_name)
        details = getattr(instance.die_requisition, "die_requisition", None)
        if details is None:
            return []
        return [d for d in details.all() if not getattr(d, "deleted", False) and d.die_tool_id]

    def _assigned_die_tool(self, instance):
        """Prefer planning-selected tool; else first tool issued on the requisition."""
        if (
            instance.die_requisition_detail_id
            and instance.die_requisition_detail
            and instance.die_requisition_detail.die_tool_id
        ):
            return instance.die_requisition_detail.die_tool
        tools = self._requisition_tool_details(instance)
        if tools:
            return tools[0].die_tool
        return None

    def get_last_wt_kg_p_mt(self, instance):
        tool = self._assigned_die_tool(instance)
        if tool and tool.actual_kg is not None:
            return tool.actual_kg
        return None

    def get_max_wt_kg_p_mt(self, instance):
        return instance.profile_no.max_wt_kg_p_mt if instance.profile_no else None

    def get_produced_pcs(self, instance):
        # Prefer queryset annotation (list performance)
        if hasattr(instance, "produced_pcs_sum"):
            return int(instance.produced_pcs_sum or 0)

        total_produced = 0
        for production in instance.production_planning.filter(deleted=False):
            total_produced += int(production.actual_pieces or 0)
        return total_produced

    def get_remaining_pcs(self, instance):
        produced_pcs = self.get_produced_pcs(instance)
        planned_pcs = int(instance.plan_pcs or 0)
        return max(planned_pcs - produced_pcs, 0)

    def get_die_tool_assigned_in_requisition(self, instance):
        return bool(self._requisition_tool_details(instance))

    def get_die_tool_selected_in_planning(self, instance):
        return bool(
            instance.die_requisition_detail_id
            and instance.die_requisition_detail
            and instance.die_requisition_detail.die_tool_id
        )

    def get_die_tool_requisition_status(self, instance):
        if self.get_die_tool_assigned_in_requisition(instance):
            return "Assigned"
        return "Not Assigned"

    def get_die_tool_planning_status(self, instance):
        assigned = self.get_die_tool_assigned_in_requisition(instance)
        selected = self.get_die_tool_selected_in_planning(instance)
        if not assigned:
            return "N/A"
        if selected:
            return "Selected"
        return "Pending Selection"

    def _workorder_payload(self, workorder):
        if not workorder:
            return None
        bill_to = workorder.bill_to
        customer = None
        if bill_to:
            customer = {
                "id": bill_to.id,
                "code": bill_to.code,
                "customer_name": bill_to.customer_name,
            }
        return {
            "id": workorder.id,
            "order_no": workorder.order_no,
            "order_date": workorder.order_date,
            "purchase_order_no": workorder.purchase_order_no,
            "purchase_order_date": workorder.purchase_order_date,
            "bill_to": customer,
            "customer": customer,
        }

    def _workorder_detail_payload(self, detail):
        if not detail:
            return None
        die_profile = detail.die_profile
        return {
            "id": detail.id,
            "length": detail.length,
            "pieces": detail.pieces,
            "net_weight": detail.net_weight,
            "die_profile": (
                {
                    "id": die_profile.id,
                    "die_number": die_profile.die_number,
                }
                if die_profile
                else None
            ),
            "alloy": _alloy_payload(detail.alloy),
            "temper": _temper_payload(detail.temper),
        }

    def _die_requisition_detail_payload(self, detail):
        if not detail:
            return None
        return {
            "id": detail.id,
            "cavity": detail.cavity,
            "die": DieSortSerializers(detail.die_tool.die).data,
            "press": _press_payload(detail.press),
            "die_tool": _die_tool_payload(detail.die_tool),
        }

    def _die_requisition_payload(self, requisition):
        if not requisition:
            return None
        details = [
            self._die_requisition_detail_payload(d)
            for d in requisition.die_requisition.all()
            if not getattr(d, "deleted", False)
        ]
        return {
            "id": requisition.id,
            "requisition_no": requisition.requisition_no,
            "status": requisition.status,
            "die_requisition_details": details,
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret["press"] = (
            instance.die_requisition_detail.press.name
            if instance.die_requisition_detail and instance.die_requisition_detail.press
            else None
        )

        # Slim nested payloads — same keys used by Planning list + Production planning dropdown
        ret["workorder"] = self._workorder_payload(instance.workorder)
        ret["workorder_detail"] = self._workorder_detail_payload(instance.workorder_detail)
        ret["die_requisition"] = self._die_requisition_payload(instance.die_requisition)
        ret["die_requisition_detail"] = self._die_requisition_detail_payload(
            instance.die_requisition_detail
        )

        ret["selected_row"] = {
            "blt_size_mm": instance.blt_size_mm,
            "blt_size_inch": instance.blt_size_inch,
            "bltWt": instance.bltWt,
            "butt_weight": instance.butt_weight,
            "actbltWt": instance.actbltWt,
            "weight_per_piece": instance.weight_per_piece,
            "total_order_weight": instance.total_order_weight,
            "ext_len_mm": instance.ext_len_mm,
            "process_loss": instance.process_loss,
            "act_ext_len": instance.act_ext_len,
            "no_of_pieces": instance.no_of_pieces,
            "pieces_weight": instance.pieces_weight,
            "process_recovery": instance.process_recovery,
            "totalWastage": instance.totalWastage,
            "totalBillets": instance.totalBillets,
            "totalKgs": instance.totalKgs,
            "billet_remarks": instance.billet_remarks
        }

        return ret

class PlanningSerializers(BaseModelSerializer):
    profile_image = serializers.CharField(
        source="profile_no.die_diagram", read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = Planning
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "profile_no",
            "profile_image",
            "die_requisition",
            "die_requisition_detail",
            "workorder",
            "workorder_detail",
            "quenching_type",
            "butt_weight_kg",
            "process_loss_mt",
            "water_pressure",
            "flow_rate",
            "planning_no",
            "planning_date",
            "plan_pcs",
            "plan_qty",
            "status",
            "cancel_status",
            "hold_status",
            "ageing",
            "remarks",
            "submitted_by",
            "submitted_at",
            "approved_by",
            "approved_at",
            "scheduled_date",
            "scheduled_by",
            "scheduled_at",
            "scheduling_remarks",
            "approval_remarks",
        ]

    def create(self, validated_data):
        selected_row = self.context["request"].data.get("selected_row", {})
        validated_data["blt_size_mm"] = selected_row.get("blt_size_mm")
        validated_data["blt_size_inch"] = selected_row.get("blt_size_inch")
        validated_data["bltWt"] = selected_row.get("bltWt")
        validated_data["butt_weight"] = selected_row.get("butt_weight")
        validated_data["actbltWt"] = selected_row.get("actbltWt")
        validated_data["weight_per_piece"] = selected_row.get("weight_per_piece")
        validated_data["total_order_weight"] = selected_row.get("total_order_weight")
        validated_data["ext_len_mm"] = selected_row.get("ext_len_mm")
        validated_data["process_loss"] = selected_row.get("process_loss")
        validated_data["act_ext_len"] = selected_row.get("act_ext_len")
        validated_data["no_of_pieces"] = selected_row.get("no_of_pieces")
        validated_data["pieces_weight"] = selected_row.get("pieces_weight")
        validated_data["process_recovery"] = selected_row.get("process_recovery")
        validated_data["totalWastage"] = selected_row.get("totalWastage")
        validated_data["totalBillets"] = selected_row.get("totalBillets")
        validated_data["totalKgs"] = selected_row.get("totalKgs")

        return super().create(validated_data)

    def update(self, instance, validated_data):
        selected_row = self.context["request"].data.get("selected_row", {})
        instance.blt_size_mm = selected_row.get("blt_size_mm", instance.blt_size_mm)
        instance.blt_size_inch = selected_row.get("blt_size_inch", instance.blt_size_inch)
        instance.bltWt = selected_row.get("bltWt", instance.bltWt)
        instance.butt_weight = selected_row.get("butt_weight", instance.butt_weight)
        instance.actbltWt = selected_row.get("actbltWt", instance.actbltWt)
        instance.weight_per_piece = selected_row.get("weight_per_piece", instance.weight_per_piece)
        instance.total_order_weight = selected_row.get("total_order_weight", instance.total_order_weight)
        instance.ext_len_mm = selected_row.get("ext_len_mm", instance.ext_len_mm)
        instance.process_loss = selected_row.get("process_loss", instance.process_loss)
        instance.act_ext_len = selected_row.get("act_ext_len", instance.act_ext_len)
        instance.no_of_pieces = selected_row.get("no_of_pieces", instance.no_of_pieces)
        instance.pieces_weight = selected_row.get("pieces_weight", instance.pieces_weight)
        instance.process_recovery = selected_row.get("process_recovery", instance.process_recovery)
        instance.totalWastage = selected_row.get("totalWastage", instance.totalWastage)
        instance.totalBillets = selected_row.get("totalBillets", instance.totalBillets)
        instance.totalKgs = selected_row.get("totalKgs", instance.totalKgs)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "profile_no" in ret:
            ret["profile_no"] = DieSortSerializers(instance.profile_no).data

        if instance.ageing:
            ret["ageing"] = AgingCycleListSerializer(instance.ageing).data

        if instance.die_requisition:
            ret["die_requisition"] = DieRequisitionSerializer(
                instance.die_requisition
            ).data
        else:
            ret["die_requisition"] = None

        if "workorder" in ret:
            ret["workorder"] = WorkOrderListSerializer(instance.workorder).data

        if "workorder_detail" in ret and instance.workorder_detail:
            ret["workorder_detail"] = WorkOrderDetailSerializers(
                instance.workorder_detail
            ).data

        ret["selected_row"] = {
            "blt_size_mm": instance.blt_size_mm,
            "blt_size_inch": instance.blt_size_inch,
            "bltWt": instance.bltWt,
            "butt_weight": instance.butt_weight,
            "actbltWt": instance.actbltWt,
            "weight_per_piece": instance.weight_per_piece,
            "total_order_weight": instance.total_order_weight,
            "ext_len_mm": instance.ext_len_mm,
            "process_loss": instance.process_loss,
            "act_ext_len": instance.act_ext_len,
            "no_of_pieces": instance.no_of_pieces,
            "pieces_weight": instance.pieces_weight,
            "process_recovery": instance.process_recovery,
            "totalWastage": instance.totalWastage,
            "totalBillets": instance.totalBillets,
            "totalKgs": instance.totalKgs,
            "billet_remarks": instance.billet_remarks
        }

        return ret


class PlanningStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planning
        fields = [
            "status",
            "scheduled_date",
            "scheduling_remarks",
            "approval_remarks",
            "approved_by",
            "approved_at",
            "submitted_by",
            "submitted_at",
        ]

    def update(self, instance, validated_data):
        request = self.context["request"]
        user = request.user
        status = validated_data.get("status")

        instance.status = status
        if status == "Scheduled":
            instance.scheduled_by = user
            instance.scheduled_at = timezone.now()
            instance.scheduled_date = validated_data.get(
                "scheduled_date", instance.scheduled_date
            )
            instance.scheduling_remarks = validated_data.get(
                "scheduling_remarks", instance.scheduling_remarks
            )

        elif status == "Approved":
            instance.approved_by = user
            instance.approved_at = timezone.now()
            instance.approval_remarks = validated_data.get(
                "approval_remarks", instance.approval_remarks
            )

        elif status == "Submitted":
            instance.submitted_by = user
            instance.submitted_at = timezone.now()

        instance.save()
        return instance
