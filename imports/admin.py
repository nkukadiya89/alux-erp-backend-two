"""
Admin interface for Import models
"""

from django.contrib import admin

from imports.models import ImportErrorRow, ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "module_name",
        "file_name",
        "status",
        "total_rows",
        "success_count",
        "error_count",
        "success_rate",
        "started_at",
        "created_by",
    ]
    list_filter = ["module_name", "status", "file_type", "started_at"]
    search_fields = ["file_name", "module_name"]
    readonly_fields = ["id", "started_at", "completed_at", "success_rate"]
    date_hierarchy = "started_at"

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("id", "module_name", "file_name", "file_type", "status")},
        ),
        (
            "Statistics",
            {"fields": ("total_rows", "success_count", "error_count", "success_rate")},
        ),
        ("Timestamps", {"fields": ("started_at", "completed_at")}),
        ("Additional", {"fields": ("created_by", "error_summary", "notes")}),
    )


@admin.register(ImportErrorRow)
class ImportErrorRowAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "import_log",
        "row_number",
        "error_type",
        "field_name",
        "error_message",
        "created_at",
    ]
    list_filter = ["error_type", "import_log__module_name", "created_at"]
    search_fields = ["error_message", "field_name", "import_log__file_name"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["import_log"]

    fieldsets = (
        (
            "Error Information",
            {
                "fields": (
                    "id",
                    "import_log",
                    "row_number",
                    "error_type",
                    "field_name",
                    "error_message",
                )
            },
        ),
        ("Raw Data", {"fields": ("raw_data",)}),
        ("Timestamp", {"fields": ("created_at",)}),
    )
