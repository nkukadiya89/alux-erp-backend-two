from django.contrib import admin
from vehicle_type.models import VehicleType
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin


class VehicleTypeResource(resources.ModelResource):
    created_by = fields.Field(attribute="created_by__first_name", column_name="Created By")
    updated_by = fields.Field(attribute="updated_by__first_name", column_name="Updated By")

    class Meta:
        model = VehicleType
        fields = ("id", "vehicle_type", "description", "created_at", "created_by", "updated_at", "updated_by")

@admin.register(VehicleType)
class VehicleTypeAdmin(ImportExportModelAdmin):
    search_fields = ("vehicle_type", "description")
    resource_class = VehicleTypeResource