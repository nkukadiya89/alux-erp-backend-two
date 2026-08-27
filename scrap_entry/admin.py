from django.contrib import admin
from .models import ScrapEntry, ScrapEntryItem, ScrapType, Process, ScrapStoreStock


class ScrapEntryItemInline(admin.TabularInline):
    model = ScrapEntryItem
    extra = 0
    autocomplete_fields = ("scrap_type", "process")
    raw_id_fields = ("item", "uom", "store")


@admin.register(ScrapEntry)
class ScrapEntryAdmin(admin.ModelAdmin):
    list_display = (
        "entry_no",
        "date",
        "plant",
        "source_department",
        "source_ref",
        "total_qty",
        "status",
        "is_archived",
        "created_at",
    )
    list_filter = ("status", "is_archived", "plant")
    search_fields = ("entry_no", "source_ref", "remarks")
    readonly_fields = ("entry_no", "total_qty", "status", "created_at", "updated_at")
    raw_id_fields = ("plant", "source_department")
    inlines = [ScrapEntryItemInline]
    date_hierarchy = "date"


@admin.register(ScrapEntryItem)
class ScrapEntryItemAdmin(admin.ModelAdmin):
    list_display = (
        "scrap_entry",
        "item",
        "scrap_type",
        "process",
        "qty",
        "uom",
        "store",
        "batch_heat",
    )
    list_filter = ("scrap_entry", "scrap_type", "process")
    search_fields = (
        "scrap_entry__entry_no",
        "item__item_code",
        "scrap_type__code",
        "process__code",
    )
    autocomplete_fields = ("scrap_entry", "scrap_type", "process")
    raw_id_fields = ("item", "uom", "store")


@admin.register(ScrapType)
class ScrapTypeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "is_archived",
        "created_at",
        "updated_at",
    )
    list_display_links = ("code", "name")
    list_filter = ("is_archived", "category")
    search_fields = ("code", "name", "category__category_code")
    autocomplete_fields = ("category",)
    list_per_page = 20
    ordering = ("code",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("code", "name", "category")}),
        ("Status", {"fields": ("is_archived",)}),
        ("Audit", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_archived", "created_at", "updated_at")
    list_display_links = ("code", "name")
    list_filter = ("is_archived",)
    search_fields = ("code", "name")
    list_per_page = 20
    ordering = ("code",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("code", "name")}),
        ("Status", {"fields": ("is_archived",)}),
        ("Audit", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(ScrapStoreStock)
class ScrapStoreStockAdmin(admin.ModelAdmin):
    list_display = ("store", "item", "quantity", "updated_at")
    search_fields = ("store__store_code", "item__item_code")
    raw_id_fields = ("store", "item")
