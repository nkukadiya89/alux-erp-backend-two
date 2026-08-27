from django.contrib import admin

from .models import (
    AdditiveCategory,
    AdditiveMaster,
    FuelType,
    Furnace,
    FurnaceType,
    MaterialType,
    RecoveryStandard,
)


@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(FurnaceType)
class FurnaceTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(FuelType)
class FuelTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Furnace)
class FurnaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "furnace_code",
        "furnace_name",
        "furnace_type",
        "status",
        "is_archived",
    )
    search_fields = ("furnace_code", "furnace_name")
    list_filter = ("status", "furnace_type", "is_archived")


@admin.register(AdditiveCategory)
class AdditiveCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(AdditiveMaster)
class AdditiveMasterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "additive_code",
        "additive_name",
        "category",
        "status",
        "is_archived",
    )
    search_fields = ("additive_code", "additive_name")
    list_filter = ("status", "category", "is_archived")


@admin.register(RecoveryStandard)
class RecoveryStandardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "furnace_type",
        "material_type",
        "min_recovery",
        "max_recovery",
        "standard_loss",
        "status",
        "is_archived",
    )
    list_filter = ("material_type", "status", "furnace_type", "is_archived")
    search_fields = ("material_type__name", "material_type__code")
