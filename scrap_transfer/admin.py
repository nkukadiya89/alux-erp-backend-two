from django.contrib import admin
from .models import ScrapTransfer, ScrapTransferItem


class ScrapTransferItemInline(admin.TabularInline):
    model = ScrapTransferItem
    extra = 0
    raw_id_fields = ("scrap_item", "uom")


@admin.register(ScrapTransfer)
class ScrapTransferAdmin(admin.ModelAdmin):
    list_display = (
        "transfer_no",
        "transfer_date",
        "from_store",
        "to_plant",
        "to_store",
        "total_qty",
        "status",
        "is_archived",
        "created_at",
    )
    list_filter = ("status", "is_archived", "to_plant")
    search_fields = ("transfer_no", "remarks")
    readonly_fields = ("transfer_no", "total_qty", "status", "created_at", "updated_at")
    raw_id_fields = ("from_store", "to_plant", "to_store", "created_by", "updated_by")
    inlines = [ScrapTransferItemInline]
    date_hierarchy = "transfer_date"


@admin.register(ScrapTransferItem)
class ScrapTransferItemAdmin(admin.ModelAdmin):
    list_display = (
        "scrap_transfer",
        "scrap_item",
        "batch_heat",
        "transfer_qty",
        "uom",
        "remarks",
    )
    list_filter = ("scrap_transfer",)
    search_fields = ("scrap_transfer__transfer_no", "scrap_item__item_code")
    raw_id_fields = ("scrap_transfer", "scrap_item", "uom")
