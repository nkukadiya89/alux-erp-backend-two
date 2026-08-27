"""
Plant Capability Views
Handles CRUD operations for Plant Capability Master
"""

import csv
import logging
from io import StringIO

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.models import ArchiveMixin, PlantCapability
from common.serializers import PlantCapabilitySerializer
from common.services.plant_capability_service import can_delete_capability
from settings.views import BaseModelViewSet
from utils.custom_filters import CustomSearchFilter
from utils.download_pdf import render_to_pdf
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class PlantCapabilityViewSet(BaseModelViewSet, ArchiveMixin):
    """
    ViewSet for Plant Capability Master
    """

    queryset = (
        PlantCapability.objects.filter(is_deleted=False)
        .select_related("created_by", "updated_by")
        .order_by("code")
    )
    serializer_class = PlantCapabilitySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    fy_filtering_enabled = False
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "status", "created_at"]
    ordering = ["code"]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change status of a plant capability"""
        try:
            instance = self.get_object()
            new_status = request.data.get("status")

            if new_status not in ["Active", "Inactive"]:
                return Response(
                    {
                        "success": False,
                        "message": "Status must be 'Active' or 'Inactive'.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if instance.status == new_status:
                return Response(
                    {
                        "success": False,
                        "message": f"Capability is already {new_status}.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.status = new_status
            instance.updated_at = timezone.now()
            instance.updated_by = request.user
            instance.save()

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Plant Capability",
                description=f"Changed status of Plant Capability '{instance.code}' to {new_status}",
                request=request,
                payload=payload,
            )

            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": f"Plant Capability status changed to {new_status}.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, code, name for active plant capabilities"""
        queryset = self.get_queryset().filter(status="Active")

        # Apply any additional filters if needed
        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param) | queryset.filter(
                code__icontains=filter_param
            )

        data = [
            {"id": str(cap.id), "code": cap.code, "name": cap.name} for cap in queryset
        ]
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """Export Plant Capabilities to Excel (CSV format)"""
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="plant_capabilities_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["Code", "Name", "Description", "Status", "Created At"])

        for cap in queryset:
            writer.writerow(
                [
                    cap.code or "",
                    cap.name or "",
                    cap.description or "",
                    cap.status or "",
                    (
                        cap.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if cap.created_at
                        else ""
                    ),
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request):
        """Export Plant Capabilities to PDF"""
        queryset = self.filter_queryset(self.get_queryset())

        data = []
        for cap in queryset:
            data.append(
                [
                    cap.code or "",
                    cap.name or "",
                    cap.description or "",
                    cap.status or "",
                    (
                        cap.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if cap.created_at
                        else ""
                    ),
                ]
            )

        context = {
            "title": "Plant Capabilities List",
            "headers": ["Code", "Name", "Description", "Status", "Created At"],
            "data": data,
            "now": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        pdf_response = render_to_pdf("master_export_pdf.html", context)
        if pdf_response:
            pdf_response["Content-Disposition"] = (
                f'attachment; filename="plant_capabilities_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
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

    def _archive_plant_capabilities(self, plant_capability_ids, user):
        """Archive plant capabilities and return updated count and codes"""
        plant_capabilities = PlantCapability.objects.filter(
            id__in=plant_capability_ids, is_deleted=False
        )

        if not plant_capabilities.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active plant capabilities found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        # Check if any are referenced by active records
        referenced_capabilities = []
        for capability in plant_capabilities:
            can_delete, error_message = can_delete_capability(capability)
            if not can_delete:
                referenced_capabilities.append(f"{capability.code}")

        if referenced_capabilities:
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": f"Cannot archive plant capabilities referenced by active records: {', '.join(referenced_capabilities)}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        archived_codes = list(plant_capabilities.values_list("code", flat=True))
        updated_count = plant_capabilities.update(
            is_deleted=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive plant capabilities"""
        try:
            plant_capability_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_codes, error_response = (
                    self._archive_plant_capabilities(plant_capability_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Plant Capability",
                    description=f"Archived {updated_count} plant capability(ies): {', '.join(archived_codes)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} plant capability(ies) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_plant_capabilities(self, plant_capability_ids, user):
        """Restore plant capabilities and return updated count and codes"""
        plant_capabilities = PlantCapability.objects.filter(
            id__in=plant_capability_ids, is_deleted=True
        )

        if not plant_capabilities.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived plant capabilities found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_codes = list(plant_capabilities.values_list("code", flat=True))
        updated_count = plant_capabilities.update(
            is_deleted=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived plant capabilities"""
        try:
            plant_capability_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_codes, error_response = (
                    self._restore_plant_capabilities(plant_capability_ids, request.user)
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Plant Capability",
                    description=f"Restored {updated_count} plant capability(ies): {', '.join(restored_codes)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = PlantCapability.objects.filter(
                id__in=plant_capability_ids
            )
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} plant capability(ies) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived plant capabilities"""
        try:
            queryset = (
                PlantCapability.objects.filter(is_deleted=True)
                .select_related("created_by", "updated_by")
                .order_by("-updated_at")
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
        """Get details of a specific archived plant capability"""
        try:
            instance = (
                PlantCapability.objects.filter(id=pk, is_deleted=True)
                .select_related("created_by", "updated_by")
                .first()
            )

            if not instance:
                return Response(
                    {
                        "success": False,
                        "message": "Archived plant capability not found",
                    },
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
                "module": "PlantCapability",
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
                "module": "PlantCapability",
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
        """Bulk import plant capabilities from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.plant_capability_importer import (
                PlantCapabilityImporter,
            )

            importer = PlantCapabilityImporter(file, user=request.user, dry_run=dry_run)
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
                "module": "PlantCapability",
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
        """Get import logs for PlantCapability module"""
        from imports.models import ImportLog

        logs = (
            ImportLog.objects.filter(module_name="PlantCapability")
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
        Note: pk here is import_log_id, not plant_capability_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="PlantCapability"
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
        Note: pk here is import_log_id, not plant_capability_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="PlantCapability")
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

        writer.writerow(
            ["Row Number", "Error Type", "Field Name", "Error Message", "Raw Data"]
        )

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
            f'attachment; filename="plantcapability_import_errors_{import_log_id}.csv"'
        )
        return response
