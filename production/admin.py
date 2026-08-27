from django.contrib import admin
from production.models import Production
from import_export import resources
from import_export.admin import ImportExportModelAdmin

class ProductionResource(resources.ModelResource):
    class Meta:
        model = Production
        fields = (
            "id",
            "production_no",
            "planning__planning_no",
            "press__name",
            "workorder__order_no",
            "customer__customer_name",
            "die_profile__die_number",
            "die_tool__tool_number",
            "cavity",
            "alloy__alloy_code",
            "temper__temper_code_new",
            "quenching_type",
            "billet_temp",
            "die_temp",
            "die_station_no",
            "time_in",
            "time_out",
            "total_cycle",
            "running_time",
            "ext_pressure",
            "cut_length",
            "pieces",
            "actual_pieces",
            "weight_per_piece",
            "weight",
            "weight_per_meter",
            "total_output_weight",
            "recovery",
            "planning_recovery",
            "production_process_recovery",
            "scrap",
            "speed",
            "input_kg_per_hour",
            "output_kg_per_hour",
            "cast_no",
            "die_tool_return_status",
            "operators__first_name",
            "shift__shift_name",
            "remarks",
            "created_at",
            "updated_at",
        )

    class Meta:
        model = Production

@admin.register(Production)
class ProductionAdmin(ImportExportModelAdmin):
    resource_class = ProductionResource
    search_fields = ("production_no", "workorder__workorder_no")

