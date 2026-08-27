import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from die.permissions import DieSizePermission,SectionPressPermission,SectionCategoriesPermission, SectionSubCategoriesPermission, DieGroupPermission
from rest_framework.permissions import IsAuthenticated
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die.filters import DiePressFilter
from die.master_serializers import (
    DieCategorySerializers,
    DieGroupSerializers,
    DiePressDropdownSerializer,
    DiePressSerializers,
    DieSizeSerializers,
    DieSubCategorySerializers,
    DieTypeSerializers,
)
from utils.export_excel import ExportUtility
from die.models import DieCategory, DieGroup, DiePress, DieSize, DieSubCategory, DieType
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
logger = logging.getLogger("file")

class DieGroupViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (DieGroup.objects.all().select_related("created_by"))
    serializer_class = DieGroupSerializers

    search_fields = BaseModelViewSet.serching_fields + ["id", "name"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "name"]
    permission_classes = [IsAuthenticated, DieGroupPermission]

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "name",
            "description",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Name", "name"),
            ("Description", "description"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="section_group.xlsx",
            sheet_name="Section Group",
        )    
        

class DieSizeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (DieSize.objects.all().select_related("created_by"))
    serializer_class = DieSizeSerializers
    search_fields = BaseModelViewSet.serching_fields + ["die_height", "die_width"]
    ordering_fields = BaseModelViewSet.ordering_fields + ["die_height", "die_width"]
    permission_classes = [IsAuthenticated, DieSizePermission]

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "die_height",
            "die_width",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Die Height", "die_height"),
            ("Die Width", "die_width"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="die-size.xlsx",
            sheet_name="Die Size",
        )

class DieCategoryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        DieCategory.objects.all()
        .select_related("created_by")
        .order_by("-id")
    )
    serializer_class = DieCategorySerializers
    search_fields = ["id", "name"]
    ordering_fields = ["id", "name"]
    permission_classes = [IsAuthenticated, SectionCategoriesPermission]

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "name",
            "description",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Name", "name"),
            ("Description", "description"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="Die_category.xlsx",
            sheet_name="Die Category",
        )


class DieSubCategoryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        DieSubCategory.objects.all()
        .select_related("created_by", "updated_by")
        .order_by("-created_at")
    )
    serializer_class = DieSubCategorySerializers
    fy_filtering_enabled = False

    search_fields = BaseModelViewSet.serching_fields + ["name"]

    ordering_fields = BaseModelViewSet.ordering_fields + ["name"]
    permission_classes = [IsAuthenticated, SectionSubCategoriesPermission]

    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
            "name",
            "description",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        )

        columns = [
            ("Sr. No.", "sr_no"),
            ("Name", "name"),
            ("Description", "description"),
            ("Created At", "created_at"),
            ("Created By", "created_by__full_name"),
            ("Updated At", "updated_at"),
            ("Updated By", "updated_by__full_name"),
        ]

        return ExportUtility.export_excel(
            queryset=queryset,
            columns=columns,
            filename="die-subcategory.xlsx",
            sheet_name="Die SubCategory",
        )


class DieTypeViewSet(BaseModelViewSet):
    queryset = (
        DieType.objects.all()
        .select_related("created_by", "updated_by")
        .order_by("-created_at")
    )
    serializer_class = DieTypeSerializers

class DiePressViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = DiePress.objects.all().select_related("created_by").order_by("-id")
    serializer_class = DiePressSerializers
    filter_backends = [DjangoFilterBackend]
    filterset_class = DiePressFilter
    ordering_fields = [
        "id",
        "code",
        "name",
        "capacity",
        "billet_diameter",
    ]
    permission_classes = [IsAuthenticated, SectionPressPermission]
    fy_filtering_enabled = False 


    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

     queryset = self.get_queryset().filter(deleted=False).values(
        "code",
        "name",
        "capacity",
        "billet_diameter",
        "billet_length_min",
        "billet_length_max",
        "billet_weight",
        "billet_wt_factor",
        "container_diameter",
        "container_area",
        "extrusion_length_min",
        "extrusion_length_max",
        "created_at",
        "created_by__full_name",
        "updated_at",
        "updated_by__full_name",
    )

     columns = [
        ("Sr. No.", "sr_no"),
        ("Code", "code"),
        ("Name", "name"),
        ("Capacity", "capacity"),
        ("Billet Diameter", "billet_diameter"),
        ("Billet Length Min", "billet_length_min"),
        ("Billet Length Max", "billet_length_max"),
        ("Billet Weight", "billet_weight"),
        ("Billet WT Factor", "billet_wt_factor"),
        ("Container Diameter", "container_diameter"),
        ("Container Area", "container_area"),
        ("Extrusion Length Min", "extrusion_length_min"),
        ("Extrusion Length Max", "extrusion_length_max"),
        ("Created At", "created_at"),
        ("Created By", "created_by__full_name"),
        ("Updated At", "updated_at"),
        ("Updated By", "updated_by__full_name"),
    ]

     return ExportUtility.export_excel(
        queryset=queryset,
        columns=columns,
        filename="die-press.xlsx",
        sheet_name="Die Press",
    )

    def _can_delete_diepress(self, diepress):
        """Check if DiePress can be deleted (not referenced by active records)"""
        from die.models import DieTool
    
        # Check DieTool
        if DieTool.objects.filter(eligible_for_press=diepress, deleted=False).exists():
            return (
                False,
                "Cannot archive DiePress. It is referenced by active Die Tool records.",
            )

        return True, None

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, code, name for active and non-archived die presses"""
        queryset = DiePress.objects.filter(deleted=False)

        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = queryset.filter(
                Q(code__icontains=filter_param) | Q(name__icontains=filter_param)
            )

        serializer = DiePressDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def _parse_dry_run_param(self, dry_run_param):
        """Helper method to parse dry_run parameter"""
        if isinstance(dry_run_param, str):
            return dry_run_param.lower() in ("true", "1", "yes")
        return bool(dry_run_param)

    def _format_import_log(self, log):
        """Helper method to format import log data"""
        from imports.models import ImportLog

        return {
            "id": str(log.id),
            "file_name": log.file_name,
            "status": log.status,
            "total_rows": log.total_rows,
            "success_count": log.success_count,
            "error_count": log.error_count,
            "success_rate": log.success_rate,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "created_by": log.created_by.id if log.created_by else None,
        }

    def _log_import_start(self, file, dry_run, user_id):
        """Log bulk import start"""
        logger.info(
            "Bulk import started",
            extra={
                "module_name": "DiePress",
                "file_name": file.name,
                "file_size": file.size,
                "dry_run": dry_run,
                "user_id": user_id,
            },
        )

    def _log_import_complete(self, result):
        """Log bulk import completion"""
        data = result.get("data", {}) if isinstance(result, dict) else {}
        logger.info(
            "Bulk import completed",
            extra={
                "module_name": "DiePress",
                "total_records": data.get("total_records", 0),
                "inserted": data.get("inserted", 0),
                "updated": data.get("updated", 0),
                "skipped": data.get("skipped", 0),
                "failed": data.get("failed", 0),
                "success_count": data.get("success_count", 0),
                "error_count": data.get("error_count", 0),
            },
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import die presses from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.die_press_importer import DiePressImporter

            importer = DiePressImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            self._log_import_complete(result)

            is_success = (
                bool(result.get("success", False))
                if isinstance(result, dict)
                else False
            )
            if not is_success:
                return self._format_import_response(
                    result,
                    is_success=False,
                    error_message=(
                        result.get("message")
                        if isinstance(result, dict)
                        else "Import failed"
                    ),
                    error_status_code=status.HTTP_400_BAD_REQUEST,
                )

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            return self._handle_import_exception(e, request)

    def _validate_import_file(self, request):
        """Validate import file"""
        if "file" not in request.FILES:
            return None, Response(
                {"success": False, "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return request.FILES["file"], None

    def _format_import_response(
        self,
        result,
        is_success,
        error_message=None,
        error_status_code=status.HTTP_400_BAD_REQUEST,
    ):
        """Format import response (matches temper_importer pattern)"""
        if not isinstance(result, dict):
            return Response(
                {"success": False, "message": error_message or "Import failed"},
                status=error_status_code,
            )

        if is_success:
            return Response(result, status=status.HTTP_200_OK)

        return Response(result, status=error_status_code)

    def _handle_import_exception(self, e, request):
        """Handle import exceptions"""
        logger.error(
            "Bulk import error",
            extra={
                "module_name": "DiePress",
                "error": str(e),
                "user_id": request.user.id if request.user else None,
            },
            exc_info=True,
        )
        return Response(
            {
                "success": False,
                "message": f"Import failed: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for DiePress module"""
        from imports.models import ImportLog

        logs = (
            ImportLog.objects.filter(module_name="DiePress")
            .select_related("created_by")
            .order_by("-started_at")
        )

        queryset = self.filter_queryset(logs)
        page = self.paginate_queryset(queryset)

        if page is not None:
            data = [self._format_import_log(log) for log in page]
            return self.get_paginated_response({"success": True, "data": data})

        data = [self._format_import_log(log) for log in queryset]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    def _format_error_row(self, row):
        """Format error row data"""
        return {
            "row_number": row.row_number,
            "error_type": row.error_type,
            "field_name": row.field_name,
            "error_message": row.error_message,
            "raw_data": row.raw_data,
        }

    @action(detail=True, methods=["get"], url_path="import-errors")
    def import_errors(self, request, pk=None):
        """
        Get errors for a specific import log.
        Note: pk here is import_log_id, not diepress_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="DiePress"
            )
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        error_rows = ImportErrorRow.objects.filter(import_log=import_log).order_by(
            "row_number"
        )

        errors = [self._format_error_row(row) for row in error_rows]
        summary = self._build_error_summary(error_rows)

        return Response(
            {"success": True, "data": {"summary": summary, "errors": errors}},
            status=status.HTTP_200_OK,
        )

    def _build_error_summary(self, error_rows):
        """Build error summary from error rows"""
        summary = {
            "total_errors": error_rows.count(),
            "error_types": {},
        }
        for row in error_rows:
            error_type = row.error_type
            summary["error_types"][error_type] = (
                summary["error_types"].get(error_type, 0) + 1
            )
        return summary

    def _validate_bulk_request(self, request):
        """Validate bulk operation request"""
        ids = request.data.get("ids", [])
        if not ids:
            return None, Response(
                {"success": False, "message": "ids field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ids, list):
            return None, Response(
                {"success": False, "message": "ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(ids) == 0:
            return None, Response(
                {"success": False, "message": "ids list cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ids, None

    def _archive_diepresses(self, diepress_ids, user):
        """Archive die presses and return updated count and names"""
        diepresses = DiePress.objects.filter(id__in=diepress_ids, deleted=False)

        if not diepresses.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active die presses found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        referenced_diepresses = []
        for diepress in diepresses:
            can_delete, error_message = self._can_delete_diepress(diepress)
            if not can_delete:
                referenced_diepresses.append(
                    f"{diepress.code or ''} - {diepress.name or ''}"
                )

        if referenced_diepresses:
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": f"Cannot archive die presses referenced by active records: {', '.join(referenced_diepresses)}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        archived_names = [f"{dp.code or ''} - {dp.name or ''}" for dp in diepresses]
        updated_count = diepresses.update(
            deleted=True,
            deleted_by=user,
            deleted_at=timezone.now(),
            updated_by=user,
            updated_at=timezone.now(),
        )

        return updated_count, archived_names, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive die presses"""
        try:
            diepress_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_names, error_response = (
                    self._archive_diepresses(diepress_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="DiePress",
                    description=f"Archived {updated_count} die press(es): {', '.join(archived_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} die press(es) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_diepresses(self, diepress_ids, user):
        """Restore archived die presses and return updated count and names"""
        diepresses = DiePress.objects.filter(id__in=diepress_ids, deleted=True)

        if not diepresses.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived die presses found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_names = [f"{dp.code or ''} - {dp.name or ''}" for dp in diepresses]
        updated_count = diepresses.update(
            deleted=False,
            deleted_by=None,
            deleted_at=None,
            updated_by=user,
            updated_at=timezone.now(),
        )

        return updated_count, restored_names, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived die presses"""
        try:
            diepress_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_names, error_response = (
                    self._restore_diepresses(diepress_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="DiePress",
                    description=f"Restored {updated_count} die press(es): {', '.join(restored_names)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = DiePress.objects.filter(id__in=diepress_ids)
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} die press(es) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived die presses"""
        try:
            queryset = (
                DiePress.objects.filter(deleted=True)
                .select_related("created_by", "deleted_by")
                .order_by("-deleted_at")
            )

            queryset = self.filter_queryset(queryset)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=True, methods=["get"], url_path="archived")
    def get_archived(self, request, pk=None):
        """Get archived die press details"""
        try:
            instance = (
                DiePress.objects.filter(id=pk, deleted=True)
                .select_related("created_by", "deleted_by")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived die press not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class DiePressArchiveViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        DiePress.objects.filter(deleted=True)
        .select_related("created_by", "deleted_by")
        .order_by("-deleted_at")
    )
    serializer_class = DiePressSerializers
    