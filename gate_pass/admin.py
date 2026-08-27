from django.contrib import admin

from .models import GatePass, GatePassItem


class GatePassItemInline(admin.TabularInline):
    model = GatePassItem
    extra = 0


@admin.register(GatePass)
class GatePassAdmin(admin.ModelAdmin):
    list_display = (
        "gate_pass_no",
        "date",
        "type",
        "status",
        "party_name",
        "vehicle_no",
        "is_archived",
        "created_at",
    )
    list_filter = ("type", "status", "is_archived", "deleted")
    search_fields = ("gate_pass_no", "party_name", "vehicle_no", "remarks")
    raw_id_fields = ("created_by", "updated_by", "deleted_by")
    inlines = [GatePassItemInline]
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@admin.register(GatePassItem)
class GatePassItemAdmin(admin.ModelAdmin):
    list_display = ("gate_pass", "description", "unit", "qty", "purpose")
    list_filter = ("gate_pass__type", "gate_pass__status")
    search_fields = ("description", "purpose", "gate_pass__gate_pass_no")
    raw_id_fields = ("gate_pass",)
