from django.contrib import admin

from return_qc.models import ReturnQC, ReturnQCLine


class ReturnQCLineInline(admin.TabularInline):
    model = ReturnQCLine
    extra = 0


@admin.register(ReturnQC)
class ReturnQCAdmin(admin.ModelAdmin):
    list_display = (
        "inspection_no",
        "inspection_date",
        "vendor",
        "overall_result",
        "deleted",
    )
    search_fields = ("inspection_no", "vehicle_no", "gate_entry_ref")
    list_filter = ("inspection_date", "overall_result", "deleted")
    inlines = [ReturnQCLineInline]
