from django.contrib import admin
from .models import ScrapSale, ScrapSaleItem, ScrapItem, ScrapStock


class ScrapSaleItemInline(admin.TabularInline):
    model = ScrapSaleItem
    extra = 0
    readonly_fields = ("total_value",)
    autocomplete_fields = ("scrap_item",)


@admin.register(ScrapSale)
class ScrapSaleAdmin(admin.ModelAdmin):
    list_display = (
        "sale_no",
        "sale_date",
        "customer",
        "dispatch_ref",
        "total_qty",
        "total_value",
        "status",
        "is_archived",
        "created_at",
    )
    list_filter = ("status", "is_archived")
    search_fields = ("sale_no", "dispatch_ref", "customer__customer_name")
    readonly_fields = (
        "sale_no",
        "total_qty",
        "total_value",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("customer",)
    inlines = [ScrapSaleItemInline]
    date_hierarchy = "sale_date"


@admin.register(ScrapItem)
class ScrapItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "item_name", "uom", "is_archived", "created_at")
    list_filter = ("is_archived",)
    search_fields = ("item_code", "item_name")


@admin.register(ScrapStock)
class ScrapStockAdmin(admin.ModelAdmin):
    list_display = ("scrap_item", "quantity", "updated_at")
    search_fields = ("scrap_item__item_code",)
    autocomplete_fields = ("scrap_item",)


@admin.register(ScrapSaleItem)
class ScrapSaleItemAdmin(admin.ModelAdmin):
    list_display = (
        "scrap_sale",
        "scrap_item",
        "sale_qty",
        "uom",
        "rate",
        "total_value",
    )
    list_filter = ("scrap_sale",)
    search_fields = ("scrap_sale__sale_no", "scrap_item__item_code")
    autocomplete_fields = ("scrap_sale", "scrap_item")
