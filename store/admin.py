from django.contrib import admin

from store.models import Store

# Register your models here.


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = [
        "store_code",
        "store_name",
        "store_type",
        "plant",
        "allows_negative_stock",
        "deleted",
        "created_at",
    ]
    list_filter = ["store_type", "deleted", "allows_negative_stock"]
    search_fields = ["store_code", "store_name", "plant__plant_name"]
    ordering = ["-created_at"]
