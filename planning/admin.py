from django.contrib import admin
from planning.models import Planning
from import_export import resources
from import_export.admin import ImportExportModelAdmin


class PlanningResource(resources.ModelResource):
    class Meta:
        model = Planning
        fields = (
            "id",
            "profile_no__die_number",
            "die_requisition__requisition_no",
            "workorder__order_no",
            "ageing__cycle_name",
            "quenching_type",
            "water_pressure",
            "flow_rate",
            "planning_no",
            "planning_date",
            "scheduled_date",
            "scheduled_by__first_name",
            "scheduled_at",
            "scheduling_remarks",
            "plan_pcs",
            "plan_qty",
            "butt_weight_kg",
            "process_loss_mt",
            "remarks",
            "status",
            "cancel_status",
            "hold_status",
            "submitted_at"
            "approved_by__first_name",
            "approved_at",
            "approval_remarks",
            "blt_size_mm",
            "blt_size_inch",
            "bltWt",
            "butt_weight",
            "actbltWt",
            "weight_per_piece",
            "total_order_weight",
            "ext_len_mm",
            "process_loss",
            "act_ext_len",
            "no_of_pieces",
            "pieces_weight",
            "process_recovery",
            "totalWastage",
            "totalBillets",
            "totalKgs",
            "billet_remarks",
        )

    class Meta:
        model = Planning

@admin.register(Planning)
class PlanningAdmin(ImportExportModelAdmin):
    resource_class = PlanningResource