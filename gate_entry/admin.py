from django.contrib import admin

from .models import GateEntry, GateEntryItem


class GateEntryItemInline(admin.TabularInline):
    model = GateEntryItem
    extra = 0


@admin.register(GateEntry)
class GateEntryAdmin(admin.ModelAdmin):
    list_display = [
        "gate_entry_no",
        "date",
        "vendor",
        "driver_name",
        "vehicle_no",
        "inward_time",
        "outward_time",
        "status",
        "is_archived",
    ]
    list_filter = ["status", "date", "deleted", "is_archived"]
    search_fields = [
        "gate_entry_no",
        "driver_name",
        "vehicle_no",
        "challan_no",
        "invoice_no",
        "vendor__person_name",
        "transporter__party_name",
    ]
    readonly_fields = ["gate_entry_no", "created_at", "updated_at", "deleted_at"]
    raw_id_fields = ["vendor", "transporter", "created_by", "updated_by", "deleted_by"]
    inlines = [GateEntryItemInline]


@admin.register(GateEntryItem)
class GateEntryItemAdmin(admin.ModelAdmin):
    list_display = ("gate_entry", "description", "unit", "qty", "purpose")
    list_filter = ("gate_entry__status", "gate_entry__date")
    search_fields = ("description", "purpose", "gate_entry__gate_entry_no")
    raw_id_fields = ("gate_entry",)
