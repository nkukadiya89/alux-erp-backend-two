from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from workorder.models import WorkOrder, WorkOrderDetail

class WorkOrderResource(resources.ModelResource):
    created_by = fields.Field(attribute="created_by__first_name", column_name="Created_By")
    updated_by = fields.Field(attribute="updated_by__first_name", column_name="Updated_By")
    deleted_by = fields.Field(attribute="deleted_by__first_name", column_name="Deleted_By")
    bill_to = fields.Field(attribute="bill_to__customer_name", column_name="Bill_To")
    ship_to = fields.Field(attribute="ship_to__customer_name", column_name="Ship_To")
    salesorder = fields.Field(attribute="salesorder__sales_order_no", column_name="SalesOrder")
    approved_by = fields.Field(attribute="approved_by__first_name", column_name="Approved_By")

    class Meta:
        model = WorkOrder
        exclude = ("reference_wo")

@admin.register(WorkOrder)
class WorkOrderAdmin(ImportExportModelAdmin):
    resource_class = WorkOrderResource
    search_fields = ("order_no", "bill_to__customer_name")

admin.site.register(WorkOrderDetail)