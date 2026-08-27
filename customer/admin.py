from django.contrib import admin
from .models import BankingDetails, ContactPerson, Customer, CustomerType
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin

class CustomerResource(resources.ModelResource):
    created_by = fields.Field(attribute="created_by__first_name", column_name="Created By")
    updated_by = fields.Field(attribute="updated_by__first_name", column_name="Updated By")
    deleted_by = fields.Field(attribute="deleted_by__first_name", column_name="Deleted By")
    customer_type = fields.Field(attribute="customer_type__name", column_name="Customer Type")
    sales_executive = fields.Field(attribute="sales_executive__first_name", column_name="Sales Executive")
    sales_executive_assistant = fields.Field(attribute="sales_executive_assistant__first_name", column_name="Sales Executive Assistant")

    class Meta:
        model = Customer

@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource
    search_fields = ("customer_name", "code")
    list_display = ("customer_name", "code", "gst_type", "gstin_number")

admin.site.register(ContactPerson)
admin.site.register(BankingDetails)
admin.site.register(CustomerType)
