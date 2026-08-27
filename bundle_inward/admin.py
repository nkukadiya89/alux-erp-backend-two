from django.contrib import admin
from bundle_inward.models import BundleInward, ExcessStock
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin

class BundleInwardResource(resources.ModelResource):
    created_by = fields.Field(attribute="created_by__first_name", column_name="Created By")
    updated_by = fields.Field(attribute="updated_by__first_name", column_name="Updated By")
    workorder = fields.Field(attribute="workorder__order_no", column_name="WorkOrder")  
    section = fields.Field(attribute="workorder_detail__die_profile__die_number", column_name="Section")
    alloy = fields.Field(attribute="workorder_detail__alloy__alloy_code", column_name="Alloy")
    temper = fields.Field(attribute="workorder_detail__temper__temper_code_new", column_name="Temper")

    class Meta:
        model = BundleInward
        exclude = ("shift")

@admin.register(BundleInward)
class BundleInwardAdmin(ImportExportModelAdmin):
    resource_class = BundleInwardResource

admin.site.register(ExcessStock)
