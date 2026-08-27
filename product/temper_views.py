import csv
import logging
from io import StringIO
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from product.models import Temper
from product.serializers import TemperDropdownSerializer, TemperSerializers
from utils.custom_filters import CustomSearchFilter
from utils.download_pdf import render_to_pdf
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class TemperViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Temper.objects.all()
        .select_related(
            "created_by", "updated_by", "deleted_by", "section_type",
            "alloy", "standard", "dimention_unit", "yield_unit"
            )
        )

    serializer_class = TemperSerializers
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [AllowAny]
    fy_filtering_enabled = False

    search_fields = [
        "id",
        "description",
        "area",
        "alloy__alloy_code",
        "alloy__color_code",
        "dimention_unit__uom_name",
        "elongation_50mm_min",
        "elongation_min",
        "hardness",
        "section_thickness_over",
        "section_thickness_upto",
        "tensile_min",
        "tensile_max",
        "yield_min",
        "yield_max",
        "yield_unit__name",
        "electrical_conductivity_min",
        "electrical_conductivity_max",
        "temper_code_old",
        "temper_code_new",
        "heat_treatment",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "id",
        "name",
        "alloy",
        "color_code",
        "section_type",
        "area",
        "dimention_unit",
        "elongation_50mm_min",
        "elongation_min",
        "hardness",
        "section_thickness_over",
        "section_thickness_upto",
        "tensile_min",
        "tensile_max",
        "yield_min",
        "yield_max",
        "yield_unit",
        "electrical_conductivity_min",
        "electrical_conductivity_max",
        "temper_code_old",
        "temper_code_new",
        "heat_treatment",
        "deleted",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = (
            Temper.objects.all()
            .select_related(
                "created_by", "updated_by", "deleted_by", "section_type",
                "alloy", "standard", "dimention_unit", "yield_unit"
                )
            )

        alloy_id = self.request.query_params.get("alloy_id")

        if alloy_id:
            queryset = queryset.filter(alloy_id=alloy_id)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def check_references(self, instance):
        """Check if Temper can be deleted (not referenced by active records)"""
        from bundle_inward.models import ExcessStock
        from die.models import ConversionRate
        from inquiry_quotation.models import InquiryQuotationDetail
        from inquiry_salesorder.models import InquirySalesOrderDetail
        from production.models import Production
        from proforma.models import ProformaDetails
        from quotation.models import QuotationDetail
        from workorder.models import WorkOrderDetail

        if Production.objects.filter(grade=instance, deleted=False).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Production records.",
            )

        if WorkOrderDetail.objects.filter(temper=instance, deleted=False).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Work Order records.",
            )

        if QuotationDetail.objects.filter(temper=instance, deleted=False).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Quotation records.",
            )

        if ProformaDetails.objects.filter(temper=instance, deleted=False).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Proforma records.",
            )

        if InquirySalesOrderDetail.objects.filter(
            temper=instance, deleted=False
        ).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Inquiry Sales Order records.",
            )

        if InquiryQuotationDetail.objects.filter(
            temper=instance, deleted=False
        ).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Inquiry Quotation records.",
            )

        if ExcessStock.objects.filter(temper=instance, deleted=False).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Excess Stock records.",
            )

        if ConversionRate.objects.filter(temper=instance, deleted=False).exists():
            return (
                False,
                "Cannot archive Temper. It is referenced by active Conversion Rate records.",
            )

        return True, None

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, name, code for active and non-archived tempers"""
        queryset = Temper.objects.filter(deleted=False)

        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = queryset.filter(code__icontains=filter_param) | queryset.filter(
                code__icontains=filter_param
            )

        serializer = TemperDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """Export Tempers to Excel (CSV format)"""
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="tempers_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["Name", "Section Type", "Created At"])

        for temper in queryset:
            writer.writerow(
                [
                    temper.name or "",
                    temper.section_type.name if temper.section_type else "",
                    (
                        temper.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if temper.created_at
                        else ""
                    ),
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request):
        """Export Tempers to PDF"""
        queryset = self.filter_queryset(self.get_queryset())

        data = []
        for temper in queryset:
            data.append(
                [
                    temper.name or "",
                    temper.section_type.name if temper.section_type else "",
                    (
                        temper.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if temper.created_at
                        else ""
                    ),
                ]
            )

        context = {
            "title": "Tempers List",
            "headers": ["Name", "Section Type", "Created At"],
            "data": data,
            "now": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        pdf_response = render_to_pdf("master_export_pdf.html", context)
        if pdf_response:
            pdf_response["Content-Disposition"] = (
                f'attachment; filename="tempers_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
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

    def _archive_tempers(self, temper_ids, user):
        """Archive tempers and return updated count and names"""
        tempers = Temper.objects.filter(id__in=temper_ids, deleted=False)

        if not tempers.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active tempers found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        referenced_tempers = []
        for temper in tempers:
            can_delete, error_message = self.check_references(temper)
            if not can_delete:
                referenced_tempers.append(f"{temper.temper_code_new}")

        if referenced_tempers:
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": f"Cannot archive tempers referenced by active records: {', '.join(referenced_tempers)}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        archived_names = list(tempers.values_list("temper_code_new", flat=True))
        updated_count = tempers.update(
            deleted=True,
            deleted_by=user,
            deleted_at=timezone.now(),
            updated_by=user,
            updated_at=timezone.now(),
        )

        return updated_count, archived_names, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive tempers"""
        try:
            temper_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_names, error_response = self._archive_tempers(
                    temper_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Temper",
                    description=f"Archived {updated_count} temper(s): {', '.join(archived_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} temper(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_tempers(self, temper_ids, user):
        """Restore archived tempers and return updated count and names"""
        tempers = Temper.objects.filter(id__in=temper_ids, deleted=True)

        if not tempers.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived tempers found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_names = list(tempers.values_list("temper_code_new", flat=True))
        updated_count = tempers.update(
            deleted=False,
            deleted_by=None,
            deleted_at=None,
        )

        return updated_count, restored_names, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived tempers"""
        try:
            temper_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_names, error_response = self._restore_tempers(
                    temper_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Temper",
                    description=f"Restored {updated_count} temper(s): {', '.join(restored_names)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = Temper.objects.filter(id__in=temper_ids)
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} temper(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived tempers"""
        try:
            queryset = (
                Temper.objects.filter(deleted=True)
                .select_related("created_by", "deleted_by", "section_type")
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
        """Get archived temper details"""
        try:
            instance = (
                Temper.objects.filter(id=pk, deleted=True)
                .select_related("created_by", "deleted_by", "section_type")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived temper not found"},
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
                "module": "Temper",
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
                "module": "Temper",
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import tempers from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.temper_importer import TemperImporter

            importer = TemperImporter(file, user=request.user, dry_run=dry_run)
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
        """Format import response (CustomerType-style)"""
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
                "module": "Temper",
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
        """Get import logs for Temper module"""
        from imports.models import ImportLog

        logs = (
            ImportLog.objects.filter(module_name="Temper")
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
        Note: pk here is import_log_id, not temper_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Temper"
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
        Note: pk here is import_log_id, not temper_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Temper")
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
            f'attachment; filename="temper_import_errors_{import_log_id}.csv"'
        )
        return response


class TemperArchiveViewSet(ArchiveMixin):
    """
    ViewSet for Archived Tempers (soft deleted)
    Read-only access to archived tempers
    """

    queryset = (
        Temper.objects.filter(deleted=True)
        .select_related("created_by", "deleted_by", "section_type", "alloy")
        .order_by("-deleted_at")
    )
    serializer_class = TemperSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = ["temper_code_new", "created_by__first_name", "created_by__last_name"]
    ordering_fields = ["temper_code_new", "created_at", "updated_at", "deleted_at"]
    ordering = ["-deleted_at"]
    http_method_names = ["get"]

    def get_queryset(self):
        """Filter archived tempers"""
        queryset = super().get_queryset()
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived tempers with pagination"""
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
        """Retrieve a single archived temper"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
