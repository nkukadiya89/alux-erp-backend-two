"""
Department Master Views
Handles CRUD operations for Department Master
"""

import csv
import logging
from io import StringIO

from django.db import models, transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.models import Department, Plant
from common.serializers import DepartmentDropdownSerializer, DepartmentSerializer
from common.services.department_service import (
    can_archive_department,
    can_deactivate_department,
)
from imports.models import ImportErrorRow, ImportLog
from imports.services.department_importer import DepartmentImporter
from utils.custom_filters import CustomSearchFilter
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class DepartmentViewSet(ModelViewSet):
    queryset = (
        Department.objects.filter(is_archived=False)
        .select_related("plant", "parent_department", "created_by", "updated_by")
        .order_by("-created_at")
    )
    serializer_class = DepartmentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = ["status", "department_type", "plant"]
    search_fields = [
        "department_code",
        "department_name",
        "cost_center_code",
        "status",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = [
        "department_name",
        "department_code",
        "created_at",
        "updated_at",
        "department_type",
        "plant",
        "parent_department",
        "status",
        "cost_center_code",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-created_at")
        return queryset.filter(is_archived=False)

    def get_serializer_class(self):
        """Use full serializer for all operations"""
        return DepartmentSerializer

    def list(self, request, *args, **kwargs):
        """List all departments with pagination, filtering, and search"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset, many=True
        )
        response_data = {"success": True, "data": serializer.data}

        if page is not None:
            return self.get_paginated_response(response_data)

        return Response(response_data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single department detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Create a new department"""
        try:
            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(created_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Department",
                description=f"Created department '{instance.department_code} - {instance.department_name}'",
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
        """Update a department (full update)"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(updated_by=request.user)
            instance.refresh_from_db()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Department",
                description=f"Updated department '{instance.department_code} - {instance.department_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.__class__(instance).data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def partial_update(self, request, *args, **kwargs):
        """Partial update a department"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(updated_by=request.user)
            instance.refresh_from_db()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Department",
                description=f"Updated department '{instance.department_code} - {instance.department_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.__class__(instance).data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Soft delete (archive) a department"""
        try:
            instance = self.get_object()

            can_archive, error_message = can_archive_department(instance)
            if not can_archive:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.is_archived = True
            instance.updated_by = request.user
            instance.updated_at = timezone.now()
            instance.save()

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="Department",
                description=f"Archived department '{instance.department_code} - {instance.department_name}'",
                request=request,
                payload=None,
            )

            return Response(
                {"success": True, "message": "Department archived successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Department is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_department(instance)
            if not can_deactivate:
                return False, error_message

        return True, None

    def _update_status_and_log(self, instance, new_status, request):
        """Update department status and log activity"""
        instance.status = new_status
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        payload = clean_payload(request.data)
        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="Department",
            description=f"Changed department status to '{new_status}' for '{instance.department_code} - {instance.department_name}'",
            request=request,
            payload=payload,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change department status (Active/Inactive)"""
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
        """Lightweight dropdown API - returns only id, department_code, department_name for active and non-archived departments"""
        queryset = self.get_queryset().filter(status="Active", is_archived=False)

        # Filter by plant_id if provided
        plant_id = request.query_params.get("plant_id")
        if plant_id:
            queryset = queryset.filter(plant_id=plant_id)

        serializer = DepartmentDropdownSerializer(queryset, many=True)
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
                "module": "Department",
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
                "module_name": "Department",
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
                    "module_name": "Department",
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
        """Bulk import departments from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = DepartmentImporter(file, user=request.user, dry_run=dry_run)
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
        """Get import logs for Department module"""
        logs = (
            ImportLog.objects.filter(module_name="Department")
            .select_related("created_by")
            .order_by("-started_at")
        )

        # Do not use self.filter_queryset(logs) here because it applies Department filters to ImportLog model
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
        Note: pk here is import_log_id, not department_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Department"
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
        Note: pk here is import_log_id, not department_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Department")
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
            f'attachment; filename="department_import_errors_{import_log_id}.csv"'
        )
        return response

    def _validate_bulk_request(self, request):
        """Validate bulk request data"""
        department_ids = request.data.get("ids", [])

        if not department_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(department_ids, list):
            return None, Response(
                {
                    "success": False,
                    "message": "ids must be a list",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return department_ids, None

    def _archive_departments(self, department_ids, user):
        """Archive departments and return updated count and codes"""
        departments = Department.objects.filter(
            id__in=department_ids, is_archived=False
        ).select_related("created_by", "updated_by")

        if not departments.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active departments found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        # Validate each department can be archived
        validation_error = self._validate_archive_operation(departments)
        if validation_error:
            return None, None, validation_error

        archived_codes = list(departments.values_list("department_code", flat=True))
        updated_count = departments.update(
            is_archived=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_codes, None

    def _validate_archive_operation(self, departments):
        """Validate that all departments can be archived"""
        for department in departments:
            can_archive, error_message = can_archive_department(department)
            if not can_archive:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"Cannot archive department '{department.department_code}': "
                            f"{error_message}"
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive (soft delete) departments"""
        try:
            department_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_codes, error_response = (
                    self._archive_departments(department_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Department",
                    description=f"Archived {updated_count} department(s): {', '.join(archived_codes)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} department(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_departments(self, department_ids, user):
        """Restore archived departments and return updated count and codes"""
        departments = Department.objects.filter(id__in=department_ids, is_archived=True)

        if not departments.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived departments found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_codes = list(departments.values_list("department_code", flat=True))
        updated_count = departments.update(
            is_archived=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived departments"""
        try:
            department_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_codes, error_response = (
                    self._restore_departments(department_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Department",
                    description=f"Restored {updated_count} department(s): {', '.join(restored_codes)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = Department.objects.filter(id__in=department_ids)
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} department(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _apply_archived_filters(self, queryset, request):
        """Apply filters to archived departments queryset"""
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        department_type_filter = request.query_params.get("department_type")
        if department_type_filter:
            queryset = queryset.filter(department_type=department_type_filter)

        plant_filter = request.query_params.get("plant")
        if plant_filter:
            queryset = queryset.filter(plant_id=plant_filter)

        return queryset

    def _apply_archived_search(self, queryset, request):
        """Apply search to archived departments queryset"""
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(department_code__icontains=search)
                | models.Q(department_name__icontains=search)
                | models.Q(cost_center_code__icontains=search)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived departments"""
        try:
            queryset = (
                Department.objects.filter(is_archived=True)
                .select_related(
                    "plant", "parent_department", "created_by", "updated_by"
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
        """Get archived department details"""
        try:
            instance = (
                Department.objects.filter(id=pk, is_archived=True)
                .select_related(
                    "plant", "parent_department", "created_by", "updated_by"
                )
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived department not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class DepartmentArchiveViewSet(ModelViewSet):
    """
    ViewSet for Archived Departments (soft deleted)
    Read-only access to archived departments
    """

    queryset = (
        Department.objects.filter(is_archived=True)
        .select_related("plant", "parent_department", "created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = DepartmentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["status", "department_type", "plant"]
    search_fields = [
        "department_code",
        "department_name",
        "cost_center_code",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = ["department_name", "department_code", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]  # Read-only - only GET for list/retrieve

    def get_queryset(self):
        """Filter archived departments"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived departments with pagination"""
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
        """Retrieve a single archived department"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
