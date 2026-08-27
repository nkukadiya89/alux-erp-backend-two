from django.contrib import admin

from common.models import (
    UOM,
    Country,
    Currency,
    Department,
    FinancialYearModel,
    ItemCategory,
    JobWorkType,
    PackingMode,
    Plant,
    PlantCapability,
    PlantType,
    PlantTypeCapability,
    SectionType,
    YieldUnit,
)

# Register your models here.
admin.site.register(Country)
admin.site.register(Currency)
admin.site.register(FinancialYearModel)
admin.site.register(PackingMode)
admin.site.register(Plant)
admin.site.register(PlantType)
admin.site.register(PlantCapability)
admin.site.register(PlantTypeCapability)
admin.site.register(UOM)
admin.site.register(YieldUnit)


@admin.register(JobWorkType)
class JobWorkTypeAdmin(admin.ModelAdmin):
    """Admin interface for Job Work Type master."""

    list_display = ["name", "discription"]
    search_fields = ["name", "discription"]
    ordering = ["name"]


admin.site.register(SectionType)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Department Master
    """

    list_display = [
        "department_code",
        "department_name",
        "department_type",
        "plant",
        "parent_department_display",
        "status",
        "is_archived",
        "created_by",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "department_type",
        "status",
        "is_archived",
        "plant",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "department_code",
        "department_name",
        "cost_center_code",
        "plant__plant_code",
        "plant__plant_name",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "department_code",
                    "department_name",
                    "department_type",
                    "plant",
                    "cost_center_code",
                    "parent_department",
                    "status",
                    "is_archived",
                )
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "id",
                    "created_by",
                    "updated_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    actions = [
        "archive_selected",
        "restore_selected",
        "activate_selected",
        "deactivate_selected",
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related(
            "plant", "parent_department", "created_by", "updated_by"
        )

    def parent_department_display(self, obj):
        """Display parent department code and name"""
        if obj.parent_department:
            return f"{obj.parent_department.department_code} - {obj.parent_department.department_name}"
        return "-"

    parent_department_display.short_description = "Parent Department"

    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by on save"""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Archive selected departments")
    def archive_selected(self, request, queryset):
        """Archive selected departments"""
        from django.utils import timezone

        from common.services.department_service import can_archive_department

        archived_count = 0
        errors = []

        for department in queryset:
            if department.is_archived:
                continue

            can_archive, error_message = can_archive_department(department)
            if can_archive:
                department.is_archived = True
                department.updated_by = request.user
                department.updated_at = timezone.now()
                department.save()
                archived_count += 1
            else:
                errors.append(f"{department.department_code}: {error_message}")

        if archived_count > 0:
            self.message_user(
                request,
                f"Successfully archived {archived_count} department(s).",
                level="success",
            )
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", level="error")


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Item Category Master
    """

    list_display = [
        "category_code",
        "category_name",
        "allowed_item_type",
        "status",
        "is_archived",
        "created_by",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "allowed_item_type",
        "status",
        "is_archived",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "category_code",
        "category_name",
        "description",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "category_code",
                    "category_name",
                    "allowed_item_type",
                    "description",
                    "is_archived",
                )
            },
        ),
    )
    actions = [
        "archive_selected",
        "restore_selected",
        "activate_selected",
        "deactivate_selected",
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("created_by", "updated_by")

    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by on save"""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Archive selected item categories")
    def archive_selected(self, request, queryset):
        """Archive selected item categories"""
        from django.utils import timezone

        from common.services.item_category_service import can_archive_item_category

        archived_count = 0
        errors = []

        for category in queryset:
            if category.is_archived:
                continue

            can_archive, error_message = can_archive_item_category(category)
            if can_archive:
                category.is_archived = True
                category.updated_by = request.user
                category.updated_at = timezone.now()
                category.save()
                archived_count += 1
            else:
                errors.append(f"{category.category_code}: {error_message}")

        if archived_count > 0:
            self.message_user(
                request,
                f"Successfully archived {archived_count} item category(ies).",
                level="success",
            )
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", level="error")

    @admin.action(description="Restore selected archived item categories")
    def restore_selected(self, request, queryset):
        """Restore selected archived item categories"""
        from django.utils import timezone

        restored_count = 0
        for category in queryset:
            if category.is_archived:
                category.is_archived = False
                category.updated_by = request.user
                category.updated_at = timezone.now()
                category.save()
                restored_count += 1

        if restored_count > 0:
            self.message_user(
                request,
                f"Successfully restored {restored_count} item category(ies).",
                level="success",
            )
        else:
            self.message_user(
                request, "No archived item categories selected.", level="warning"
            )