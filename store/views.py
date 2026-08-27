import csv
import logging
from io import StringIO

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from store.models import Store
from store.serializers import StoreDropdownSerializer, StoreSerializers
from utils.custom_filters import CustomSearchFilter
from utils.download_pdf import render_to_pdf
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger(__name__)


class StoreViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Store.objects.filter(deleted=False)
        .select_related("plant", "created_by", "updated_by")
        .order_by("created_at")
    )
    serializer_class = StoreSerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    fy_filtering_enabled = False
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = BaseModelViewSet.serching_fields + [
        "id",
        "store_code",
        "store_name",
        "store_type__name",
        "plant__plant_code",
        "plant__plant_name",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "id",
        "store_code",
        "plant",
        "store_name",
        "store_type",
        "plant__plant_code",
        "plant__plant_name",
    ]

    def get_queryset(self):
        # Override BaseModelViewSet get_queryset to avoid financial year filtering
        # Stores are master data and should not be restricted by financial year dates
        queryset = (
            Store.objects.filter(deleted=False)
            .select_related("plant", "created_by", "updated_by")
            .order_by("created_at")
        )
        return queryset

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, store_code, store_name for active and non-archived stores"""
        queryset = Store.objects.filter(deleted=False)

        # Apply any additional filters if needed
        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = queryset.filter(store_name__icontains=filter_param)

        serializer = StoreDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """Export Stores to Excel (CSV format)"""
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="stores_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["Code", "Name", "Type", "Plant", "Created At"])

        for store in queryset:
            writer.writerow(
                [
                    store.store_code or "",
                    store.store_name or "",
                    store.store_type or "",
                    store.plant.plant_name if store.plant else "",
                    (
                        store.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if store.created_at
                        else ""
                    ),
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request):
        """Export Stores to PDF"""
        queryset = self.filter_queryset(self.get_queryset())

        data = []
        for store in queryset:
            data.append(
                [
                    store.store_code or "",
                    store.store_name or "",
                    store.store_type or "",
                    store.plant.plant_name if store.plant else "",
                    (
                        store.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if store.created_at
                        else ""
                    ),
                ]
            )

        context = {
            "title": "Stores List",
            "headers": ["Code", "Name", "Type", "Plant", "Created At"],
            "data": data,
            "now": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        pdf_response = render_to_pdf("master_export_pdf.html", context)
        if pdf_response:
            pdf_response["Content-Disposition"] = (
                f'attachment; filename="stores_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            )
            return pdf_response

        return Response(
            {"success": False, "message": "Failed to generate PDF"},
            status=status.HTTP_400_BAD_REQUEST,
        )

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

    def _archive_stores(self, store_ids, user):
        """Archive stores and return updated count and names"""
        stores = Store.objects.filter(id__in=store_ids, deleted=False)

        if not stores.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active stores found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        archived_names = list(stores.values_list("store_code", flat=True))
        for store in stores:
            store.deleted = True
            store.updated_by = user
            store.updated_at = timezone.now()
            store.save()
        updated_count = stores.count()

        return updated_count, archived_names, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive stores"""
        try:
            store_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_names, error_response = self._archive_stores(
                    store_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Store",
                    description=f"Archived {updated_count} store(s): {', '.join(archived_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} store(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_stores(self, store_ids, user):
        """Restore archived stores and return updated count and names"""
        stores = Store.objects.filter(id__in=store_ids, deleted=True)

        if not stores.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived stores found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_names = list(stores.values_list("store_code", flat=True))
        for store in stores:
            store.deleted = False
            store.updated_by = user
            store.updated_at = timezone.now()
            store.save()
        updated_count = stores.count()

        return updated_count, restored_names, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived stores"""
        try:
            store_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_names, error_response = self._restore_stores(
                    store_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Store",
                    description=f"Restored {updated_count} store(s): {', '.join(restored_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} store(s) restored successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="archived")
    def archived_list(self, request):
        """List archived stores"""
        try:
            queryset = (
                Store.objects.filter(deleted=True)
                .select_related("plant", "created_by", "deleted_by")
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
        """Get archived store details"""
        try:
            instance = (
                Store.objects.filter(id=pk, deleted=True)
                .select_related("plant", "created_by", "deleted_by")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived store not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

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
                "module": "Store",
                "file_name": file.name,
                "file_size": file.size,
                "dry_run": dry_run,
                "user_id": user_id,
            },
        )

    def _log_import_complete(self, result):
        """Log bulk import completion"""
        logger.info(
            "Bulk import completed",
            extra={
                "module": "Store",
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import stores from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.store_importer import StoreImporter

            importer = StoreImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            self._log_import_complete(result)

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
        """Format import response"""
        if is_success and result:
            return Response(
                {
                    "success": True,
                    "message": "Import completed successfully",
                    "data": {
                        "total_rows": result.get("total_rows", 0),
                        "success_count": result.get("success_count", 0),
                        "error_count": result.get("error_count", 0),
                        "import_log_id": str(result.get("import_log_id", "")),
                    },
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": error_message or "Import failed",
                },
                status=error_status_code,
            )

    def _handle_import_exception(self, e, request):
        """Handle import exceptions"""
        logger.error(
            "Bulk import error",
            extra={
                "module": "Store",
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
        """Get import logs for Store module"""
        from imports.models import ImportLog

        logs = (
            ImportLog.objects.filter(module_name="Store")
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
        Note: pk here is import_log_id, not store_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Store"
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

    @action(detail=True, methods=["get"], url_path="error-report/download")
    def download_error_report(self, request, pk=None):
        """
        Download error report as CSV.
        Note: pk here is import_log_id, not store_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Store")
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        error_rows = ImportErrorRow.objects.filter(import_log=import_log).order_by(
            "row_number"
        )

        return self._generate_csv_response(error_rows, pk)

    def _generate_csv_response(self, error_rows, import_log_id):
        """Generate CSV response for error report"""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            ["Row Number", "Error Type", "Field Name", "Error Message", "Raw Data"]
        )

        # Write error rows
        for row in error_rows:
            writer.writerow(
                [
                    row.row_number,
                    row.error_type,
                    row.field_name or "",
                    row.error_message,
                    str(row.raw_data) if row.raw_data else "",
                ]
            )

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="store_import_errors_{import_log_id}.csv"'
        )
        return response


class StoreArchiveViewSet(ArchiveMixin):
    """
    ViewSet for Archived Stores (soft deleted)
    Read-only access to archived stores
    """

    queryset = (
        Store.objects.filter(deleted=True)
        .select_related("plant", "created_by")
        .order_by("-updated_at")
    )
    serializer_class = StoreSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = [
        "store_code",
        "store_name",
        "created_by__first_name",
        "created_by__last_name",
    ]
    ordering_fields = ["store_code", "store_name", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]  # Read-only - only GET for list/retrieve

    def get_queryset(self):
        """Filter archived stores"""
        queryset = super().get_queryset()
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived stores with pagination"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
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

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single archived store"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
