from django.contrib import admin

from jobwork_invoice.models import JobworkInvoice, JobworkInvoiceLine


class JobworkInvoiceLineInline(admin.TabularInline):
    model = JobworkInvoiceLine
    extra = 0


@admin.register(JobworkInvoice)
class JobworkInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "challan_no",
        "challan_date",
        "vendor",
        "jobwork_type",
        "total_amount",
        "deleted",
    )
    search_fields = ("challan_no", "vendor_invoice_no", "vehicle_no")
    list_filter = ("challan_date", "deleted")
    inlines = [JobworkInvoiceLineInline]


@admin.register(JobworkInvoiceLine)
class JobworkInvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("id", "jobwork_invoice", "production", "pieces", "total_weight")
    search_fields = ("jobwork_invoice__challan_no", "production__production_no")
