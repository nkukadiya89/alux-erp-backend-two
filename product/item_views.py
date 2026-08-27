import csv
import logging
from django.db import transaction
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

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from imports.services.item_importer import ItemImporter
from imports.utils import validate_file_extension
from product.models import Item, ItemType, MaterialCenter, ValuationMethod
from product.serializers import (
    ItemDropdownSerializer,
    ItemSerializers,
    ItemTypeQuickSerializer,
    MaterialCenterQuickSerializer,
    ValuationMethodQuickSerializer,
)
from product.services.item_services import can_archive_item, can_deactivate_item
from utils.custom_filters import CustomSearchFilter
from utils.download_pdf import render_to_pdf
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger(__name__)


class ItemViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = Item.objects.all()
    serializer_class = ItemSerializers
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    fy_filtering_enabled = False
    filterset_fields = [
        "item_code",
        "item_name",
        "uom__uom_name",
        "alloy_code",
        "heat_tracking",
        "reorder_level",
        "status",
        "hsn_code",
        "gst_rate",
        "base_unit",
        "net_weight",
        "purchase_rate",
        "sale_rate",
        "minimum_stock",
        "maximum_stock",
        "reorder_qty",
        "valuation_method__name",
        "making_time_minutes",
        "lead_time_days",
        "bom_required",
        "material_center__name",
        "batch_managed",
        "grn_required",
        "category__category_code",
        "item_type__name",
        "uom",
        "status",
        "item_type",
    ]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "item_code",
        "item_name",
        "item_type__name",
        "category__category_code",
        "category__category_name",
        "uom__uom_code",
        "uom__uom_name",
        "alloy_code",
        "status",
        "hsn_code",
        "gst_rate",
        "net_weight",
        "reorder_level",
        "purchase_rate",
        "base_unit",
        "sale_rate",
        "minimum_stock",
        "maximum_stock",
        "reorder_qty",
        "valuation_method__name",
        "material_center__name",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "item_code",
        "item_name",
        "item_type",
        "category",
        "uom",
        "alloy_code",
        "heat_tracking",
        "reorder_level",
        "status",
        "hsn_code",
        "gst_rate",
        "base_unit",
        "net_weight",
        "purchase_rate",
        "sale_rate",
        "valuation_method",
        "minimum_stock",
        "maximum_stock",
        "reorder_qty",
        "making_time_minutes",
        "lead_time_days",
        "bom_required",
        "material_center",
        "batch_managed",
        "grn_required",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(deleted=False)
            .select_related(
                "created_by",
                "updated_by",
                "category",
                "uom",
                "item_type",
                "valuation_method",
                "material_center",
            )
            .order_by("-created_at")
        )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(created_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Item",
                description=f"Created Item '{instance.item_code} - {instance.item_name}'",
                request=request,
                payload=clean_payload(request.data),
            )
            return Response(
                {
                    "success": True,
                    "message": "Item Created Successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_data = ItemSerializers(instance).data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save(updated_by=request.user)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Item",
                description=f"Updated Item '{instance.item_code} - {instance.item_name}'",
                request=request,
                payload={
                    "old_data": clean_payload(old_data),
                    "new_data": clean_payload(serializer.data),
                },
            )
            return Response(
                {
                    "success": True,
                    "message": "Item Updated Successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        """Soft delete (archive) an Item"""
        try:
            instance = self.get_object()
            can_archive, error_message = can_archive_item(instance)
            if not can_archive:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.deleted = True
            instance.deleted_by = request.user
            instance.deleted_at = timezone.now()
            instance.save()

            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name="Item",
                description=f"Archived Item '{instance.item_code} - {instance.item_name}'",
                request=request,
                payload=clean_payload(request.data),
            )

            return Response(
                {"success": True, "message": "Item archived successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """
        Lightweight API for Item dropdown - returns only active and non-deleted records.
        Query param: type=SCRAP to filter by category allowed_item_type (e.g. for Scrap Entry).
        """
        try:
            queryset = (
                Item.objects.filter(deleted=False, status=True)
                .select_related("category", "uom")
                .order_by("item_code")
            )
            item_type = request.query_params.get("type", "").strip().upper()
            if item_type:
                queryset = queryset.filter(category__allowed_item_type=item_type)
            serializer = ItemDropdownSerializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """Export Items to Excel (CSV format)"""
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="items_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            ["Code", "Name", "Type", "Category", "Default UOM", "Active", "Created At"]
        )

        for item in queryset:
            writer.writerow(
                [
                    item.item_code or "",
                    item.item_name or "",
                    item.item_type or "",
                    item.category.category_name if item.category else "",
                    item.uom.uom_code if item.uom else "",
                    item.status,
                    (
                        item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if item.created_at
                        else ""
                    ),
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request):
        """Export Items to PDF"""
        queryset = self.filter_queryset(self.get_queryset())

        data = []
        for item in queryset:
            data.append(
                [
                    item.item_code or "",
                    item.item_name or "",
                    item.item_type or "",
                    item.category.category_name if item.category else "",
                    "Yes" if item.status else "No",
                    (
                        item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if item.created_at
                        else ""
                    ),
                ]
            )

        context = {
            "title": "Items List",
            "headers": ["Code", "Name", "Type", "Category", "Active", "Created At"],
            "data": data,
            "now": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        pdf_response = render_to_pdf("master_export_pdf.html", context)
        if pdf_response:
            pdf_response["Content-Disposition"] = (
                f'attachment; filename="items_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            )
            return pdf_response

        return Response(
            {"success": False, "message": "Failed to generate PDF"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Item is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_item(instance)
            if not can_deactivate:
                return False, error_message
        return True, None

    def _update_status_and_log(self, instance, new_status, request):
        """Update Item status and log activity"""
        instance.status = new_status
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        payload = clean_payload(request.data)
        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="Item",
            description=f"Changed Item status to '{new_status}' for '{instance.item_code} - {instance.item_name}'",
            request=request,
            payload=payload,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change Item status (Active/Inactive)"""
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

    def _validate_bulk_request(self, request):
        """Validate bulk archive/restore request"""
        item_ids = request.data.get("ids", [])
        if not item_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids field is required and cannot be empty",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(item_ids, list):
            return None, Response(
                {"success": False, "message": "ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return item_ids, None

    def _validate_archive_operation(self, items):
        """Validate that all items can be archived"""
        for item in items:
            can_archive, error_message = can_archive_item(item)
            if not can_archive:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"Cannot archive item '{item.item_code}': "
                            f"{error_message}"
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return None

    def _archive_items(self, item_ids, user):
        """Archive Items and return updated count and names"""
        items = Item.objects.filter(id__in=item_ids, deleted=False)

        if not items.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active Items found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        validation_error = self._validate_archive_operation(items)
        if validation_error:
            return None, None, validation_error

        archived_names = list(items.values_list("item_code", flat=True))
        updated_count = items.update(
            deleted=True,
            deleted_by=user,
            deleted_at=timezone.now(),
            updated_by=user,
            updated_at=timezone.now(),
        )

        return updated_count, archived_names, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive Items"""
        try:
            item_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_names, error_response = self._archive_items(
                    item_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="ARCHIVE",
                    module_name="Item",
                    description=f"Archived {updated_count} Item(s): {', '.join(archived_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} Item(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_items(self, item_ids, user):
        """Restore archived Items and return updated count and names"""
        items = Item.objects.filter(id__in=item_ids, deleted=True)

        if not items.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived Items found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_names = list(items.values_list("item_code", flat=True))
        updated_count = items.update(
            deleted=False,
            deleted_by=None,
            deleted_at=None,
            updated_by=user,
            updated_at=timezone.now(),
        )

        return updated_count, restored_names, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived Items"""
        try:
            item_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_names, error_response = self._restore_items(
                    item_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Item",
                    description=f"Restored {updated_count} Item(s): {', '.join(restored_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} Item(s) restored successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(methods=["post"], detail=True, url_path="unarchive")
    def unarchive(self, request, pk=None):
        """Unarchive (restore) a single archived Item"""
        try:
            instance = Item.objects.get(pk=pk, deleted=True)
        except Item.DoesNotExist:
            return Response(
                {"success": False, "message": "Archived Item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        instance.deleted = False
        instance.deleted_by = None
        instance.deleted_at = None
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        log_user_activity(
            user=request.user,
            action="RESTORE",
            module_name="Item",
            description=f"Unarchived Item '{instance.item_code} - {instance.item_name}'",
            request=request,
            payload=clean_payload(request.data),
        )

        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Item unarchived successfully.",
                "data": serializer.data,
            },
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
            "module_name": log.module_name,
            "file_name": log.file_name,
            "status": log.status,
            "total_rows": log.total_rows,
            "success_count": log.success_count,
            "error_count": log.error_count,
            "created_by": (
                {
                    "id": log.created_by.id,
                    "name": log.created_by.get_full_name(),
                }
                if log.created_by
                else None
            ),
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request, *args, **kwargs):
        """Bulk import Items from CSV/Excel file"""
        try:
            if "file" not in request.FILES:
                return Response(
                    {"success": False, "message": "No file provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            file = request.FILES["file"]
            dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))

            if not validate_file_extension(file.name, [".xlsx", ".xls", ".csv"]):
                return Response(
                    {
                        "success": False,
                        "message": f"Invalid file type. Allowed: .xlsx, .xls, .csv",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            importer = ItemImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()

            log_user_activity(
                user=request.user,
                action="BULK_IMPORT",
                module_name="Item",
                description=f"Bulk imported Items from file '{file.name}' (dry_run={dry_run})",
                request=request,
                payload={"file_name": file.name, "dry_run": dry_run, "result": result},
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in bulk import: {str(e)}", exc_info=True)
            return custom_exception(e)

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

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request, *args, **kwargs):
        """Get import history for Item"""
        from imports.models import ImportLog

        queryset = (
            ImportLog.objects.filter(module_name="Item")
            .select_related("created_by")
            .order_by("-created_at")
        )

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
        Note: pk here is import_log_id, not item_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Item"
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
        Note: pk here is import_log_id, not item_id
        """
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Item")
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        error_rows = ImportErrorRow.objects.filter(import_log=import_log).order_by(
            "row_number"
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="item_import_errors_{import_log.id}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            ["Row Number", "Error Type", "Field Name", "Error Message", "Raw Data"]
        )

        for row in error_rows:
            writer.writerow(
                [
                    row.row_number,
                    row.error_type,
                    row.field_name,
                    row.error_message,
                    row.raw_data,
                ]
            )

        return response


class ItemArchiveViewSet(ModelViewSet):
    """
    ViewSet for Archived Items (soft deleted)
    Read-only access to archived Items
    """

    queryset = (
        Item.objects.filter(deleted=True)
        .select_related("created_by", "updated_by", "category", "uom")
        .order_by("-updated_at")
    )
    serializer_class = ItemSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["status", "item_type"]
    search_fields = ["item_code", "item_name", "item_type", "alloy_code"]
    ordering_fields = [
        "item_code",
        "item_name",
        "item_type",
        "created_at",
        "updated_at",
    ]
    ordering = ["-updated_at"]
    http_method_names = ["get"]

    def get_queryset(self):
        """Filter archived Items"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.lower() == "true")
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived Items with pagination"""
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
        """Retrieve a single archived Item"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class MaterialCenterViewSet(ModelViewSet):
    queryset = MaterialCenter.objects.all()
    serializer_class = MaterialCenterQuickSerializer
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["name"]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get"]


class ValuationMethodViewSet(ModelViewSet):
    queryset = ValuationMethod.objects.all()
    serializer_class = ValuationMethodQuickSerializer
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["name"]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get"]


class ItemTypeViewSet(ModelViewSet):
    queryset = ItemType.objects.all()
    serializer_class = ItemTypeQuickSerializer
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["name"]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get"]
