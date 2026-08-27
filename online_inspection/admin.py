from django.contrib import admin
from online_inspection.models import OnlineInspection, OnlineInspectionDetail


class OnlineInspectionDetailInline(admin.TabularInline):
    model = OnlineInspectionDetail
    extra = 0
    fields = [
        "production",
        "section",
        "rack_no",
        "cut_length_mm",
        "planned_pieces",
        "act_inspected_pieces",
        "remark",
    ]


@admin.register(OnlineInspection)
class OnlineInspectionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "inspection_date",
        "press",
        "shift_name_snapshot",
        "created_at",
    ]
    search_fields = ["inspection_date", "press__name"]
    list_filter = ["inspection_date", "press", "deleted"]
    inlines = [OnlineInspectionDetailInline]


@admin.register(OnlineInspectionDetail)
class OnlineInspectionDetailAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "online_inspection",
        "production",
        "section",
        "rack_no",
        "act_inspected_pieces",
        "created_at",
    ]
    search_fields = ["rack_no", "production__production_no", "section__die_number"]
    list_filter = ["online_inspection__inspection_date", "deleted"]
