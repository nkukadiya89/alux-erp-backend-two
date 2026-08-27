import csv
import logging
from io import StringIO
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from django.db.models import OuterRef, Subquery
from customer.filters import CustomerFilter
from customer.models import BankingDetails, Customer
from customer.serializers import (
    BankingDetailSerializer,
    CustomerDropdownSerializer,
    CustomerInfoSerializer,
    CustomerSerializer,
    QuickCustomerSerializer,
)
from die.models import ConversionRateItems, ConversionRateVersions
from imports.models import ImportErrorRow, ImportLog
from django.db.models import Prefetch
from utils.log_activity import clean_payload, log_user_activity

logger = logging.getLogger(__name__)


class CustomerViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Customer.objects.all()
        .select_related(
            "customer_type",
            "sales_executive",
            "sales_executive_assistant",
            "created_by",   
            "updated_by",   
            "deleted_by",   
        )
        .prefetch_related(
            Prefetch(
                "banking_details",
                queryset=BankingDetails.objects.filter(deleted=False)
                .select_related(
                    "created_by",
                    "updated_by",
                    "deleted_by",
                )
            ),
        )
        .order_by("-created_at")
    )

    serializer_class = CustomerSerializer
    list_serializer_class = CustomerInfoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomerFilter
    fy_filtering_enabled = False

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, customer_name, customer_number, person_name for active and non-archived customers"""
        queryset = self.get_queryset().filter(deleted=False)

        company_type = request.query_params.get("company_type")
        if company_type:
            if company_type == "vendor":
                queryset = queryset.filter(
                    company_type__in=["vendor", "customer_vendor"]
                )
            elif company_type == "customer":
                queryset = queryset.filter(
                    company_type__in=["customer", "customer_vendor"]
                )

        serializer = CustomerDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="get-conversion-rate-by-customer")
    def get_conversion_rate_by_customer(self, request, *args, **kwargs):
        customer_id = request.query_params.get("customer_id")
        die_id = request.query_params.get("die_id")
        alloy_id = request.query_params.get("alloy_id")
        temper_id = request.query_params.get("temper_id")

        if not customer_id:
            return Response(
                {"success": False, "message": "Customer ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"success": False, "message": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        items_filter = {"conversion_rate__customer": customer}

        if die_id:
            items_filter["die_id"] = die_id
        if alloy_id:
            items_filter["alloy_id"] = alloy_id
        if temper_id:
            items_filter["temper_id"] = temper_id

        latest_version = ConversionRateVersions.objects.filter(
            conversion_rate_items=OuterRef("pk")
        ).order_by("-date", "-created_at", "-id")

        items = ConversionRateItems.objects.filter(**items_filter).annotate(
            latest_version_id=Subquery(latest_version.values("id")[:1]),
            latest_conversion=Subquery(latest_version.values("conversion")[:1]),
        )

        data = [
            {
                "conversion": item.latest_conversion,
            }
            for item in items
        ]

        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="quick-customer-add")
    def quick_customer_add(self, request, *args, **kwargs):
        data = request.data

        serializer = QuickCustomerSerializer(data=data, context={"request": request})

        serializer.is_valid(raise_exception=True)
        customer = serializer.save(created_by=request.user)

        payload = clean_payload(request.data)

        log_user_activity(
            user=request.user,
            action="CREATE",
            module_name="Customer",
            description=f"Created Customer '{customer.customer_name}'",
            request=request,
            payload=payload,
        )
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_201_CREATED,
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
        """Format import response with row-level error details"""
        if is_success and result:
            row_errors = []

            if result.get("import_log_id"):
                try:
                    from imports.models import ImportErrorRow

                    error_rows = ImportErrorRow.objects.filter(
                        import_log_id=result.get("import_log_id")
                    ).order_by("row_number", "id")

                    errors_by_row = {}
                    for error_row in error_rows:
                        row_num = error_row.row_number
                        if row_num not in errors_by_row:
                            errors_by_row[row_num] = []
                        errors_by_row[row_num].append(
                            {
                                "field": error_row.field_name,
                                "error_type": error_row.error_type,
                                "message": error_row.error_message,
                            }
                        )

                    for row_num in sorted(errors_by_row.keys()):
                        row_errors.append(
                            {
                                "row_number": row_num,
                                "errors": errors_by_row[row_num],
                                "error_count": len(errors_by_row[row_num]),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error fetching import errors: {str(e)}")

            response_data = {
                "import_log_id": str(result.get("import_log_id", "")),
                "total_rows": result.get("total_rows", 0),
                "inserted": result.get("inserted", 0),
                "updated": result.get("updated", 0),
                "skipped": result.get("skipped", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
                "dry_run": result.get("dry_run", False),
            }

            if row_errors:
                response_data["row_errors"] = row_errors[:50]
                if len(row_errors) > 50:
                    response_data["row_errors_truncated"] = True
                    response_data["total_error_rows"] = len(row_errors)

            return Response(
                {
                    "success": True,
                    "message": result.get("message", "Import completed successfully"),
                    "data": response_data,
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

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import customers from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))

        logger.info(
            "Bulk import started",
            extra={
                "module_name": "Customer",
                "file_name": file.name if hasattr(file, "name") else "unknown",
                "file_size": file.size if hasattr(file, "size") else 0,
                "dry_run": dry_run,
                "user_id": request.user.id,
            },
        )

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.customer_importer import CustomerImporter

            importer = CustomerImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()

            logger.info(
                "Bulk import completed",
                extra={
                    "module_name": "Customer",
                    "success": result.get("success"),
                    "total_rows": result.get("total_rows", 0),
                    "success_count": result.get("success_count", 0),
                    "error_count": result.get("error_count", 0),
                },
            )

            return self._format_import_response(result, is_success=True)
        except ValueError as e:
            logger.warning(
                f"Validation error in bulk import: {str(e)}",
                extra={
                    "module_name": "Customer",
                    "user_id": request.user.id,
                },
                exc_info=True,
            )
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(
                "Error in bulk import",
                extra={
                    "module_name": "Customer",
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

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Customer module"""
        logs = (
            ImportLog.objects.filter(module_name="Customer")
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
        Note: pk here is import_log_id, not customer_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Customer"
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
        Note: pk here is import_log_id, not customer_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Customer")
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
            f'attachment; filename="customer_import_errors_{import_log_id}.csv"'
        )
        return response

class BankingDetailViewSet(BaseModelViewSet):
    queryset = BankingDetails.objects.all().select_related("customer")
    serializer_class = BankingDetailSerializer
