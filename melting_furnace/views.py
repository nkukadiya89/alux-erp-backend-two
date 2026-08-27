import csv
from io import StringIO
import logging

from django.db import models, transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from imports.models import ImportErrorRow, ImportLog
from imports.services.additive_master_importer import AdditiveMasterImporter
from imports.services.furnace_importer import FurnaceImporter
from imports.services.recovery_standard_importer import RecoveryStandardImporter
from melting_furnace.services.additive_master_service import (
    can_archive_additive_master,
    can_deactivate_additive_master,
)
from melting_furnace.services.furnace_service import (
    can_archive_furnace,
    can_deactivate_furnace,
    can_delete_furnace,
)
from melting_furnace.services.recovery_standard_service import (
    can_archive_recovery_standard,
    can_deactivate_recovery_standard,
    can_delete_recovery_standard,
)
from utils.custom_filters import CustomSearchFilter
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

from .models import (
    AdditiveCategory,
    AdditiveMaster,
    FuelType,
    Furnace,
    FurnaceType,
    MaterialType,
    RecoveryStandard,
)
from .serializers import (
    AdditiveCategoryDropdownSerializer,
    AdditiveMasterDropdownSerializer,
    AdditiveMasterSerializer,
    FuelTypeDropdownSerializer,
    FurnaceDropdownSerializer,
    FurnaceSerializer,
    FurnaceTypeDropdownSerializer,
    MaterialTypeSerializer,
    RecoveryStandardDropdownSerializer,
    RecoveryStandardSerializer,
)

# Create your views here.
logger = logging.getLogger(__name__)


class FurnaceViewSet(ModelViewSet):
    queryset = (
        Furnace.objects.filter(deleted=False)
        .select_related("created_by", "updated_by")
        .order_by("furnace_code")
    )
    serializer_class = FurnaceSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = [
        "furnace_name",
        "furnace_code",
        "furnace_type__name",
        "furnace_capacity",
        "fuel_type__name",
        "min_temperature",
        "max_temperature",
        "status",
    ]
    search_fields = [
        "furnace_name",
        "furnace_code",
        "furnace_type__name",
        "furnace_capacity",
        "fuel_type__name",
        "min_temperature",
        "max_temperature",
        "status",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = [
        "furnace_name",
        "furnace_code",
        "furnace_type__name",
        "furnace_capacity",
        "fuel_type__name",
        "min_temperature",
        "max_temperature",
        "status",
        "created_at",
    ]
    ordering = ["-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(deleted=False)

    def get_serializer_class(self):
        """Use full serializer for all operations"""
        return FurnaceSerializer

    def list(self, request, *args, **kwargs):
        """List all furnaces with pagination, filtering, and search"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response(
                {"success": True, "data": paginated_response.data},
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single furnace detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Create a new furnace"""
        try:
            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(created_by=request.user, updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Furnace",
                description=f"Created furnace '{instance.furnace_code} - {instance.furnace_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        """Update a furnace (full update)"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Furnace",
                description=f"Updated furnace '{instance.furnace_code} - {instance.furnace_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def partial_update(self, request, *args, **kwargs):
        """Partial update a furnace"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Furnace",
                description=f"Updated furnace '{instance.furnace_code} - {instance.furnace_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Soft delete (archive) a furnace"""
        try:
            instance = self.get_object()

            can_archive, error_message = can_archive_furnace(instance)
            if not can_archive:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.deleted = True
            instance.updated_by = request.user
            instance.updated_at = timezone.now()
            instance.save()

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="Furnace",
                description=f"Archived furnace '{instance.furnace_code} - {instance.furnace_name}'",
                request=request,
                payload=None,
            )

            return Response(
                {"success": True, "message": "Furnace archived successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Furnace is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_furnace(instance)
            if not can_deactivate:
                return False, error_message

        return True, None

    def _update_status_and_log(self, instance, new_status, request):
        """Update furnace status and log activity"""
        instance.status = new_status
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        payload = clean_payload(request.data)
        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="Furnace",
            description=f"Changed furnace status to '{new_status}' for '{instance.furnace_code} - {instance.furnace_name}'",
            request=request,
            payload=payload,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change furnace status (Active/Inactive)"""
        try:
            instance = self.get_object()
            new_status = request.data.get("status")

            if not new_status:
                return Response(
                    {"success": False, "message": "status field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            is_valid, error_message = self._validate_status_change(instance, new_status)
            if not is_valid:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self._update_status_and_log(instance, new_status, request)
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, furnace_code, furnace_name for active and non-archived furnaces"""
        queryset = self.get_queryset().filter(status="Active", deleted=False)

        serializer = FurnaceDropdownSerializer(queryset, many=True)
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
                "module": "Furnace",
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
                "module_name": "Furnace",
                "success": result.get("success"),
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    def _handle_import_exception(self, e, request):
        """Handle bulk import exceptions"""
        if isinstance(e, ValueError):
            logger.warning(f"Validation error in bulk import: {str(e)}", exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.error(
                "Error in bulk import",
                extra={
                    "module_name": "Furnace",
                    "error": str(e),
                    "user_id": request.user.id,
                },
                exc_info=True,
            )
            return self._format_import_response(
                None,
                is_success=False,
                error_message="Internal server error during import",
                error_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import furnaces from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = FurnaceImporter(file, user=request.user, dry_run=dry_run)
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
                    "message": result.get("message", "Import completed successfully"),
                    "data": {
                        "import_log_id": str(result.get("import_log_id", "")),
                        "total_rows": result.get("total_rows", 0),
                        "success_count": result.get("success_count", 0),
                        "error_count": result.get("error_count", 0),
                        "dry_run": result.get("dry_run", False),
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

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Furnace module"""
        logs = (
            ImportLog.objects.filter(module_name="Furnace")
            .select_related("created_by")
            .order_by("-started_at")
        )

        # Do not use self.filter_queryset(logs) here because it applies Furnace filters to ImportLog model
        queryset = logs
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
        Note: pk here is import_log_id, not furnace_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Furnace"
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
        Note: pk here is import_log_id, not furnace_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Furnace")
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
            f'attachment; filename="furnace_import_errors_{import_log_id}.csv"'
        )
        return response

    def _validate_bulk_request(self, request):
        """Validate bulk request data"""
        furnace_ids = request.data.get("ids", [])

        if not furnace_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(furnace_ids, list):
            return None, Response(
                {
                    "success": False,
                    "message": "ids must be a list",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return furnace_ids, None

    def _archive_furnaces(self, furnace_ids, user):
        """Archive furnaces and return updated count and codes"""
        furnaces = Furnace.objects.filter(
            id__in=furnace_ids, deleted=False
        ).select_related("created_by", "updated_by")

        if not furnaces.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active furnaces found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        # Validate each furnace can be archived
        validation_error = self._validate_archive_operation(furnaces)
        if validation_error:
            return None, None, validation_error

        archived_codes = list(furnaces.values_list("furnace_code", flat=True))
        updated_count = furnaces.update(
            deleted=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_codes, None

    def _validate_archive_operation(self, furnaces):
        """Validate that all furnaces can be archived"""
        for furnace in furnaces:
            can_archive, error_message = can_archive_furnace(furnace)
            if not can_archive:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"Cannot archive furnace '{furnace.furnace_code}': "
                            f"{error_message}"
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive (soft delete) furnaces"""
        try:
            furnace_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_codes, error_response = self._archive_furnaces(
                    furnace_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Furnace",
                    description=f"Archived {updated_count} furnace(s): {', '.join(archived_codes)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} furnace(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_furnaces(self, furnace_ids, user):
        """Restore archived furnaces and return updated count and codes"""
        furnaces = Furnace.objects.filter(id__in=furnace_ids, deleted=True)

        if not furnaces.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived furnaces found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_codes = list(furnaces.values_list("furnace_code", flat=True))
        updated_count = furnaces.update(
            deleted=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived furnaces"""
        try:
            furnace_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_codes, error_response = self._restore_furnaces(
                    furnace_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Furnace",
                    description=f"Restored {updated_count} furnace(s): {', '.join(restored_codes)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = Furnace.objects.filter(id__in=furnace_ids)
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} furnace(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _apply_archived_filters(self, queryset, request):
        """Apply filters to archived furnaces queryset"""
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def _apply_archived_search(self, queryset, request):
        """Apply search to archived furnaces queryset"""
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(furnace_code__icontains=search)
                | models.Q(furnace_name__icontains=search)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived furnaces"""
        try:
            queryset = (
                Furnace.objects.filter(deleted=True)
                .select_related("created_by", "updated_by")
                .order_by("-updated_at")
            )

            queryset = self._apply_archived_filters(queryset, request)

            ordering = request.query_params.get("ordering", "-updated_at")
            queryset = queryset.order_by(ordering)
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
        """Get archived furnace details"""
        try:
            instance = (
                Furnace.objects.filter(id=pk, deleted=True)
                .select_related("created_by", "updated_by")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived furnace not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class AdditiveMasterViewSet(ModelViewSet):
    queryset = (
        AdditiveMaster.objects.filter(deleted=False)
        .select_related("created_by", "updated_by")
        .order_by("-id")
    )
    serializer_class = AdditiveMasterSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = [
        "additive_code",
        "additive_name",
        "category__name",
        "unit__uom_name",
        "standard_quantity",
        "min_limit",
        "max_limit",
        "status",
    ]
    search_fields = [
        "additive_code",
        "additive_name",
        "category__name",
        "unit__uom_name",
        "standard_quantity",
        "min_limit",
        "max_limit",
        "status",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = [
        "additive_code",
        "additive_name",
        "category__name",
        "unit__uom_name",
        "standard_quantity",
        "min_limit",
        "max_limit",
        "status",
        "created_at",
    ]
    ordering = ["-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(deleted=False)

    def get_serializer_class(self):
        """Use full serializer for all operations"""
        return AdditiveMasterSerializer

    def list(self, request, *args, **kwargs):
        """List all additive master with pagination, filtering, and search"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response(
                {"success": True, "data": paginated_response.data},
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single additive master detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Create a new additive master"""
        try:
            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(created_by=request.user, updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Additive Master",
                description=f"Created additive master '{instance.additive_code} - {instance.additive_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        """Update a additive master (full update)"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Additive Master",
                description=f"Updated additive master '{instance.additive_code} - {instance.additive_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def partial_update(self, request, *args, **kwargs):
        """Partial update a additive master"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Additive Master",
                description=f"Updated additive master '{instance.additive_code} - {instance.additive_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Soft delete (archive) a additive master"""
        try:
            instance = self.get_object()

            can_archive, error_message = can_archive_additive_master(instance)
            if not can_archive:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.deleted = True
            instance.updated_by = request.user
            instance.updated_at = timezone.now()
            instance.save()

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="Additive Master",
                description=f"Archived additive master '{instance.additive_code} - {instance.additive_name}'",
                request=request,
                payload=None,
            )

            return Response(
                {"success": True, "message": "Additive master archived successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Additive master is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_additive_master(instance)
            if not can_deactivate:
                return False, error_message

        return True, None

    def _update_status_and_log(self, instance, new_status, request):
        """Update additive master status and log activity"""
        instance.status = new_status
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        payload = clean_payload(request.data)
        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="Additive Master",
            description=f"Changed additive master status to '{new_status}' for '{instance.additive_code} - {instance.additive_name}'",
            request=request,
            payload=payload,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change additive master status (Active/Inactive)"""
        try:
            instance = self.get_object()
            new_status = request.data.get("status")

            if not new_status:
                return Response(
                    {"success": False, "message": "status field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            is_valid, error_message = self._validate_status_change(instance, new_status)
            if not is_valid:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self._update_status_and_log(instance, new_status, request)
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, additive_code, additive_name for active and non-archived additive master"""
        queryset = self.get_queryset().filter(status="Active", deleted=False)

        serializer = AdditiveMasterDropdownSerializer(queryset, many=True)
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
                "module": "Additive Master",
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
                "module_name": "Additive Master",
                "success": result.get("success"),
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    def _handle_import_exception(self, e, request):
        """Handle bulk import exceptions"""
        if isinstance(e, ValueError):
            logger.warning(f"Validation error in bulk import: {str(e)}", exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.error(
                "Error in bulk import",
                extra={
                    "module_name": "Additive Master",
                    "error": str(e),
                    "user_id": request.user.id,
                },
                exc_info=True,
            )
            return self._format_import_response(
                None,
                is_success=False,
                error_message="Internal server error during import",
                error_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import additive master from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = AdditiveMasterImporter(file, user=request.user, dry_run=dry_run)
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
                    "message": result.get("message", "Import completed successfully"),
                    "data": {
                        "import_log_id": str(result.get("import_log_id", "")),
                        "total_rows": result.get("total_rows", 0),
                        "success_count": result.get("success_count", 0),
                        "error_count": result.get("error_count", 0),
                        "dry_run": result.get("dry_run", False),
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

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Additive Master module"""
        logs = (
            ImportLog.objects.filter(module_name="Additive Master")
            .select_related("created_by")
            .order_by("-started_at")
        )

        # Do not use self.filter_queryset(logs) here because it applies Additive Master filters to ImportLog model
        queryset = logs
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
        Note: pk here is import_log_id, not additive_master_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Additive Master"
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
        Note: pk here is import_log_id, not additive_master_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Additive Master")
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
            f'attachment; filename="additive_master_import_errors_{import_log_id}.csv"'
        )
        return response

    def _validate_bulk_request(self, request):
        """Validate bulk request data"""
        additive_master_ids = request.data.get("ids", [])

        if not additive_master_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(additive_master_ids, list):
            return None, Response(
                {
                    "success": False,
                    "message": "ids must be a list",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return additive_master_ids, None

    def _archive_additive_master(self, additive_master_ids, user):
        """Archive additive master and return updated count and codes"""
        additive_master = AdditiveMaster.objects.filter(
            id__in=additive_master_ids, deleted=False
        ).select_related("created_by", "updated_by")

        if not additive_master.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active additive master found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        # Validate each additive master can be archived
        validation_error = self._validate_archive_operation(additive_master)
        if validation_error:
            return None, None, validation_error

        archived_codes = list(additive_master.values_list("additive_code", flat=True))
        updated_count = additive_master.update(
            deleted=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_codes, None

    def _validate_archive_operation(self, additive_master):
        """Validate that all additive master can be archived"""
        for additive_master in additive_master:
            can_archive, error_message = can_archive_additive_master(additive_master)
            if not can_archive:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"Cannot archive additive master '{additive_master.additive_code}': "
                            f"{error_message}"
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive (soft delete) additive master"""
        try:
            additive_master_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_codes, error_response = (
                    self._archive_additive_master(additive_master_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Additive Master",
                    description=f"Archived {updated_count} additive master(s): {', '.join(archived_codes)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} additive master(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_additive_master(self, additive_master_ids, user):
        """Restore archived additive master and return updated count and codes"""
        additive_master = AdditiveMaster.objects.filter(
            id__in=additive_master_ids, deleted=True
        )

        if not additive_master.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived additive master found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_codes = list(additive_master.values_list("additive_code", flat=True))
        updated_count = additive_master.update(
            deleted=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived additive master"""
        try:
            additive_master_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_codes, error_response = (
                    self._restore_additive_master(additive_master_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Additive Master",
                    description=f"Restored {updated_count} additive master(s): {', '.join(restored_codes)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = AdditiveMaster.objects.filter(
                id__in=additive_master_ids
            )
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} additive master(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _apply_archived_filters(self, queryset, request):
        """Apply filters to archived additive master queryset"""
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def _apply_archived_search(self, queryset, request):
        """Apply search to archived additive master queryset"""
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(additive_code__icontains=search)
                | models.Q(additive_name__icontains=search)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived additive master"""
        try:
            queryset = (
                AdditiveMaster.objects.filter(deleted=True)
                .select_related("created_by", "updated_by")
                .order_by("-updated_at")
            )

            queryset = self._apply_archived_filters(queryset, request)

            ordering = request.query_params.get("ordering", "-updated_at")
            queryset = queryset.order_by(ordering)
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
        """Get archived additive master details"""
        try:
            instance = (
                AdditiveMaster.objects.filter(id=pk, deleted=True)
                .select_related("created_by", "updated_by")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived additive master not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class RecoveryStandardViewSet(ModelViewSet):
    queryset = (
        RecoveryStandard.objects.filter(deleted=False)
        .select_related("created_by", "updated_by", "furnace_type", "material_type")
        .order_by("-id")
    )
    serializer_class = RecoveryStandardSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = [
        "status",
        "furnace_type",
        "material_type",
        "min_recovery",
        "max_recovery",
        "standard_loss",
        "effective_from",
    ]
    search_fields = [
        "furnace_type__name",
        "material_type__name",
        "material_type__code",
        "min_recovery",
        "max_recovery",
        "standard_loss",
        "effective_from",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = [
        "furnace_type__name",
        "material_type__name",
        "min_recovery",
        "max_recovery",
        "standard_loss",
        "effective_from",
        "created_at",
    ]
    ordering = ["furnace_type__name", "material_type__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(deleted=False)

    def get_serializer_class(self):
        """Use full serializer for all operations"""
        return RecoveryStandardSerializer

    def list(self, request, *args, **kwargs):
        """List all recovery standards with pagination, filtering, and search"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response(
                {"success": True, "data": paginated_response.data},
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single recovery standard detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Create a new recovery standard"""
        try:
            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(created_by=request.user, updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Recovery Standard",
                description=f"Created recovery standard '{instance.furnace_type} - {instance.material_type}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        """Update a recovery standard (full update)"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Recovery Standard",
                description=f"Updated recovery standard '{instance.furnace_type} - {instance.material_type}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def partial_update(self, request, *args, **kwargs):
        """Partial update a recovery standard"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Recovery Standard",
                description=f"Updated recovery standard '{instance.furnace_type} - {instance.material_type}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Soft delete (archive) a recovery standard"""
        try:
            instance = self.get_object()

            can_archive, error_message = can_archive_recovery_standard(instance)
            if not can_archive:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.deleted = True
            instance.updated_by = request.user
            instance.updated_at = timezone.now()
            instance.save()

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="Recovery Standard",
                description=f"Archived recovery standard '{instance.furnace_type} - {instance.material_type}'",
                request=request,
                payload=None,
            )

            return Response(
                {
                    "success": True,
                    "message": "Recovery standard archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Recovery standard is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_recovery_standard(instance)
            if not can_deactivate:
                return False, error_message

        return True, None

    def _update_status_and_log(self, instance, new_status, request):
        """Update recovery standard status and log activity"""
        instance.status = new_status
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        payload = clean_payload(request.data)
        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="Recovery Standard",
            description=f"Changed recovery standard status to '{new_status}' for '{instance.furnace_type} - {instance.material_type}'",
            request=request,
            payload=payload,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change recovery standard status (Active/Inactive)"""
        try:
            instance = self.get_object()
            new_status = request.data.get("status")

            if not new_status:
                return Response(
                    {"success": False, "message": "status field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            is_valid, error_message = self._validate_status_change(instance, new_status)
            if not is_valid:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self._update_status_and_log(instance, new_status, request)
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, furnace type , material type for active and non-archived recovery standards"""
        queryset = self.get_queryset().filter(status="Active", deleted=False)

        serializer = RecoveryStandardDropdownSerializer(queryset, many=True)
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
                "module": "Recovery Standard",
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
                "module_name": "Recovery Standard",
                "success": result.get("success"),
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    def _handle_import_exception(self, e, request):
        """Handle bulk import exceptions"""
        if isinstance(e, ValueError):
            logger.warning(f"Validation error in bulk import: {str(e)}", exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.error(
                "Error in bulk import",
                extra={
                    "module_name": "Recovery Standard",
                    "error": str(e),
                    "user_id": request.user.id,
                },
                exc_info=True,
            )
            return self._format_import_response(
                None,
                is_success=False,
                error_message="Internal server error during import",
                error_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import recovery standards from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = RecoveryStandardImporter(
                file, user=request.user, dry_run=dry_run
            )
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
                    "message": result.get("message", "Import completed successfully"),
                    "data": {
                        "import_log_id": str(result.get("import_log_id", "")),
                        "total_rows": result.get("total_rows", 0),
                        "success_count": result.get("success_count", 0),
                        "error_count": result.get("error_count", 0),
                        "dry_run": result.get("dry_run", False),
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

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Recovery Standard module"""
        logs = (
            ImportLog.objects.filter(module_name="Recovery Standard")
            .select_related("created_by")
            .order_by("-started_at")
        )

        # Do not use self.filter_queryset(logs) here because it applies Recovery Standard filters to ImportLog model
        queryset = logs
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
        Note: pk here is import_log_id, not recovery_standard_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Recovery Standard"
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
        Note: pk here is import_log_id, not recovery_standard_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Recovery Standard")
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
            f'attachment; filename="recovery_standard_import_errors_{import_log_id}.csv"'
        )
        return response

    def _validate_bulk_request(self, request):
        """Validate bulk request data"""
        recovery_standard_ids = request.data.get("ids", [])

        if not recovery_standard_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(recovery_standard_ids, list):
            return None, Response(
                {
                    "success": False,
                    "message": "ids must be a list",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return recovery_standard_ids, None

    def _archive_recovery_standards(self, recovery_standard_ids, user):
        """Archive recovery standards and return updated count and codes"""
        recovery_standards = RecoveryStandard.objects.filter(
            id__in=recovery_standard_ids, deleted=False
        ).select_related("created_by", "updated_by")

        if not recovery_standards.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active recovery standards found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        # Validate each recovery standard can be archived
        validation_error = self._validate_archive_operation(recovery_standards)
        if validation_error:
            return None, None, validation_error

        archived_codes = list(
            recovery_standards.values_list("material_type__name", flat=True)
        )
        updated_count = recovery_standards.update(
            deleted=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_codes, None

    def _validate_archive_operation(self, recovery_standards):
        """Validate that all recovery standards can be archived"""
        for recovery_standard in recovery_standards:
            can_archive, error_message = can_archive_recovery_standard(
                recovery_standard
            )
            if not can_archive:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"Cannot archive recovery standard '{recovery_standard.material_type}': "
                            f"{error_message}"
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive (soft delete) recovery standards"""
        try:
            recovery_standard_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_codes, error_response = (
                    self._archive_recovery_standards(
                        recovery_standard_ids, request.user
                    )
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Recovery Standard",
                    description=f"Archived {updated_count} recovery standard(s): {', '.join(archived_codes)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} recovery standard(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_recovery_standards(self, recovery_standard_ids, user):
        """Restore archived recovery standards and return updated count and codes"""
        recovery_standards = RecoveryStandard.objects.filter(
            id__in=recovery_standard_ids, deleted=True
        )

        if not recovery_standards.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived recovery standards found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_codes = [
            f"{rs.furnace_type} - {rs.material_type}" for rs in recovery_standards
        ]
        updated_count = recovery_standards.update(
            deleted=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived recovery standards"""
        try:
            recovery_standard_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_codes, error_response = (
                    self._restore_recovery_standards(
                        recovery_standard_ids, request.user
                    )
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Recovery Standard",
                    description=f"Restored {updated_count} recovery standard(s): {', '.join(restored_codes)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = RecoveryStandard.objects.filter(
                id__in=recovery_standard_ids
            )
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} recovery standard(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _apply_archived_filters(self, queryset, request):
        """Apply filters to archived recovery standards queryset"""
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def _apply_archived_search(self, queryset, request):
        """Apply search to archived recovery standards queryset"""
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(furnace_type__name__icontains=search)
                | models.Q(material_type__name__icontains=search)
                | models.Q(material_type__code__icontains=search)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived recovery standards"""
        try:
            queryset = (
                RecoveryStandard.objects.filter(deleted=True)
                .select_related(
                    "created_by", "updated_by", "furnace_type", "material_type"
                )
                .order_by("-updated_at")
            )

            queryset = self._apply_archived_filters(queryset, request)

            ordering = request.query_params.get("ordering", "-updated_at")
            queryset = queryset.order_by(ordering)
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
        """Get archived recovery standard details"""
        try:
            instance = (
                RecoveryStandard.objects.filter(id=pk, deleted=True)
                .select_related(
                    "created_by", "updated_by", "furnace_type", "material_type"
                )
                .first()
            )

            if not instance:
                return Response(
                    {
                        "success": False,
                        "message": "Archived recovery standard not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class MaterialTypeViewSet(ModelViewSet):
    queryset = MaterialType.objects.filter().order_by("name")
    serializer_class = MaterialTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]
    ordering = ["name"]


class FurnaceTypeViewSet(ModelViewSet):
    queryset = FurnaceType.objects.filter().order_by("name")
    serializer_class = FurnaceTypeDropdownSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination


class FuelTypeViewSet(ModelViewSet):
    queryset = FuelType.objects.filter().order_by("name")
    serializer_class = FuelTypeDropdownSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination


class AdditiveCategoryViewSet(ModelViewSet):
    queryset = AdditiveCategory.objects.filter(deleted=False).order_by("name")
    serializer_class = AdditiveCategoryDropdownSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
