"""
Item Category Master Views
Handles CRUD operations for Item Category Master
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

from common.models import ItemCategory
from common.serializers import ItemCategoryDropdownSerializer, ItemCategorySerializer
from common.services.item_category_service import (
    can_archive_item_category,
    can_deactivate_item_category,
    can_delete_item_category,
)
from imports.models import ImportErrorRow, ImportLog
from imports.services.item_category_importer import ItemCategoryImporter
from imports.utils import get_file_type
from utils.custom_filters import CustomSearchFilter
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class ItemCategoryViewSet(ModelViewSet):
    queryset = (
        ItemCategory.objects.filter(is_archived=False)
        .select_related("created_by", "updated_by")
        .order_by("-created_at")
    )
    serializer_class = ItemCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["status", "allowed_item_type"]
    search_fields = [
        "category_code",
        "status",
        "category_name",
        "allowed_item_type",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = [
        "category_name",
        "status",
        "category_code",
        "created_at",
        "allowed_item_type",
        "updated_at",
        "updated_by",
        "created_by",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_archived=False)

    def get_serializer_class(self):
        """Use full serializer for all operations"""
        return ItemCategorySerializer

    def list(self, request, *args, **kwargs):
        """List all item categories with pagination, filtering, and search"""
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
        """Retrieve a single item category detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Create a new item category"""
        try:
            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(created_by=request.user)

            # Invalidate dropdown cache
            self._invalidate_dropdown_cache()

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Item Category",
                description=f"Created item category '{instance.category_code} - {instance.category_name}'",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    def _invalidate_dropdown_cache(self):
        """Invalidate all dropdown cache keys"""
        from django.core.cache import cache

        from common.models import ItemCategory

        # Get all item types and invalidate their cache keys
        item_types = ItemCategory.ITEM_TYPE_CHOICES
        cache_keys = ["item_category_dropdown_all"]
        for item_type, _ in item_types:
            cache_keys.append(f"item_category_dropdown_{item_type}")

        cache.delete_many(cache_keys)
        logger.info(
            "Item Category dropdown cache invalidated",
            extra={
                "module_name": "Item Category",
                "cache_keys": cache_keys,
            },
        )

    def update(self, request, *args, **kwargs):
        """Update an item category (full update)"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user, updated_at=timezone.now())

            # Invalidate dropdown cache if status or allowed_item_type changed
            if "status" in request.data or "allowed_item_type" in request.data:
                self._invalidate_dropdown_cache()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Item Category",
                description=f"Updated item category '{instance.category_code} - {instance.category_name}'",
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
        """Partial update an item category"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            # Invalidate dropdown cache if status or allowed_item_type changed
            if "status" in request.data or "allowed_item_type" in request.data:
                self._invalidate_dropdown_cache()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Item Category",
                description=f"Updated item category '{instance.category_code} - {instance.category_name}'",
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
        """Soft delete (archive) an item category"""
        try:
            instance = self.get_object()

            can_archive, error_message = can_archive_item_category(instance)
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
                module_name="Item Category",
                description=f"Archived item category '{instance.category_code} - {instance.category_name}'",
                request=request,
                payload=None,
            )

            return Response(
                {"success": True, "message": "Item category archived successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Category is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_item_category(instance)
            if not can_deactivate:
                return False, error_message

        return True, None

    def _update_status_and_log(self, instance, new_status, request):
        """Update category status and log activity"""
        instance.status = new_status
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()

        payload = clean_payload(request.data)
        log_user_activity(
            user=request.user,
            action="UPDATE",
            module_name="Item Category",
            description=f"Changed category status to '{new_status}' for '{instance.category_code} - {instance.category_name}'",
            request=request,
            payload=payload,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change item category status (Active/Inactive)"""
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

            # Invalidate dropdown cache when status changes
            self._invalidate_dropdown_cache()

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, category_code, category_name, allowed_item_type for active and non-archived categories"""
        from django.core.cache import cache

        # Build cache key based on item_type filter
        item_type = request.query_params.get("item_type")
        cache_key = f"item_category_dropdown_{item_type or 'all'}"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(
                "Item Category dropdown served from cache",
                extra={
                    "module_name": "Item Category",
                    "cache_key": cache_key,
                    "item_type": item_type,
                },
            )
            return Response(
                {"success": True, "data": cached_data},
                status=status.HTTP_200_OK,
            )

        # Cache miss - fetch from database
        queryset = ItemCategory.objects.filter(status="Active", is_archived=False)

        # Filter by item_type if provided
        if item_type:
            queryset = queryset.filter(allowed_item_type=item_type)

        serializer = ItemCategoryDropdownSerializer(queryset, many=True)
        data = serializer.data

        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, data, timeout=300)

        logger.info(
            "Item Category dropdown fetched from database and cached",
            extra={
                "module_name": "Item Category",
                "cache_key": cache_key,
                "item_type": item_type,
                "count": len(data),
            },
        )

        return Response(
            {"success": True, "data": data},
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
                "module_name": "Item Category",
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
                "module_name": "Item Category",
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
                    "module_name": "Item Category",
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
        """Bulk import item categories from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            # Check file size and row count for async processing
            total_rows = self._estimate_file_rows(file)
            use_async = total_rows > 1000 and not dry_run

            if use_async:
                # For large imports, use async processing
                logger.info(
                    "Large bulk import detected - using async processing",
                    extra={
                        "module_name": "Item Category",
                        "total_rows": total_rows,
                        "threshold": 1000,
                        "user_id": request.user.id,
                    },
                )

                # Save file temporarily and trigger async task
                import os
                import tempfile

                from django.core.files.storage import default_storage

                from common.tasks import bulk_import_item_categories_async
                from imports.models import ImportLog

                # Create import log first
                import_log = ImportLog.objects.create(
                    module_name="Item Category",
                    file_name=file.name,
                    file_type=getattr(file, "content_type", "unknown"),
                    status="pending",
                    created_by=request.user,
                )

                # Save file to temporary location
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(
                    temp_dir, f"item_category_import_{import_log.id}_{file.name}"
                )
                with open(temp_file_path, "wb+") as temp_file:
                    for chunk in file.chunks():
                        temp_file.write(chunk)

                # Trigger async task
                task = bulk_import_item_categories_async.delay(
                    file_path=temp_file_path,
                    user_id=request.user.id,
                    import_log_id=str(import_log.id),
                    dry_run=dry_run,
                )

                return Response(
                    {
                        "success": True,
                        "message": f"Large import queued for async processing. Task ID: {task.id}",
                        "data": {
                            "import_log_id": str(import_log.id),
                            "task_id": task.id,
                            "total_rows": total_rows,
                            "status": "queued",
                            "async": True,
                        },
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            importer = ItemCategoryImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            self._log_import_complete(result)

            # Invalidate dropdown cache after bulk import
            if result.get("success_count", 0) > 0:
                self._invalidate_dropdown_cache()

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            return self._handle_import_exception(e, request)

    def _estimate_file_rows(self, file):
        """Estimate number of rows in file (excluding header)"""
        try:
            if hasattr(file, "seek"):
                file.seek(0)

            import csv

            if file.name.endswith(".csv"):
                reader = csv.reader(file)
                row_count = sum(1 for _ in reader) - 1  # Subtract header
            else:
                # For Excel files, use pandas or openpyxl
                # For now, return a conservative estimate
                row_count = 100  # Default estimate
        except Exception:
            row_count = 100  # Default estimate
        finally:
            if hasattr(file, "seek"):
                file.seek(0)

        return max(0, row_count)

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
            response_data = {
                "success": True,
                "message": result.get("message", "Import completed successfully"),
                "data": {
                    "import_log_id": str(result.get("import_log_id", "")),
                    "total_rows": result.get("total_rows", 0),
                    "total_records": result.get("total_records", 0),
                    "inserted": result.get("inserted", 0),
                    "updated": result.get("updated", 0),
                    "skipped": result.get("skipped", 0),
                    "success_count": result.get("success_count", 0),
                    "error_count": result.get("error_count", 0),
                    "dry_run": result.get("dry_run", False),
                },
            }

            # Add row_errors with detailed field-level errors (omit category_code/category_name when N/A)
            row_errors = result.get("row_errors")
            if row_errors:
                formatted_row_errors = []
                for row_error in row_errors:
                    row_data = row_error.get("row_data") or {}
                    cat_code = row_data.get("category_code") or row_data.get(
                        "Category Code"
                    )
                    cat_name = row_data.get("category_name") or row_data.get(
                        "Category Name"
                    )
                    formatted_error = {
                        "row_number": row_error.get("row_number"),
                        "errors": [],
                    }
                    if cat_code and str(cat_code).strip() and str(cat_code) != "N/A":
                        formatted_error["category_code"] = cat_code
                    if cat_name and str(cat_name).strip() and str(cat_name) != "N/A":
                        formatted_error["category_name"] = cat_name

                    for error in row_error.get("errors", []):
                        formatted_error["errors"].append(
                            {
                                "field": error.get("field", "unknown"),
                                "message": error.get("message", "Validation failed"),
                                "value": error.get("value"),
                            }
                        )

                    formatted_row_errors.append(formatted_error)

                response_data["data"]["row_errors"] = formatted_row_errors

            return Response(response_data, status=status.HTTP_200_OK)
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
        """Get import logs for Item Category module"""
        logs = (
            ImportLog.objects.filter(module_name="Item Category")
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
        Note: pk here is import_log_id, not category_id
        """
        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="Item Category"
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
        Note: pk here is import_log_id, not category_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Item Category")
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
            f'attachment; filename="item_category_import_errors_{import_log_id}.csv"'
        )
        return response

    def _validate_bulk_request(self, request):
        """Validate bulk request data"""
        category_ids = request.data.get("ids", [])

        if not category_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(category_ids, list):
            return None, Response(
                {
                    "success": False,
                    "message": "ids must be a list",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return category_ids, None

    def _archive_categories(self, category_ids, request):
        """Archive multiple categories"""
        categories = ItemCategory.objects.filter(id__in=category_ids, is_archived=False)

        archived_count = 0
        errors = []

        for category in categories:
            can_archive, error_message = can_archive_item_category(category)
            if can_archive:
                category.is_archived = True
                category.updated_by = request.user
                category.updated_at = timezone.now()
                category.save()
                archived_count += 1
            else:
                errors.append(f"{category.category_code}: {error_message}")

        return archived_count, errors

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request):
        """Bulk archive item categories"""
        try:
            category_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                archived_count, errors = self._archive_categories(category_ids, request)

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="Item Category",
                description=f"Bulk archived {archived_count} item categories",
                request=request,
                payload=payload,
            )

            message = f"Successfully archived {archived_count} item category(ies)."
            if errors:
                message += f" {len(errors)} failed: {', '.join(errors[:5])}"

            return Response(
                {
                    "success": True,
                    "message": message,
                    "data": {
                        "archived_count": archived_count,
                        "errors": errors,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_categories(self, category_ids, request):
        """Restore multiple categories"""
        categories = ItemCategory.objects.filter(id__in=category_ids, is_archived=True)

        restored_count = 0
        for category in categories:
            category.is_archived = False
            category.updated_by = request.user
            category.updated_at = timezone.now()
            category.save()
            restored_count += 1

        return restored_count

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        """Bulk restore archived item categories"""
        try:
            category_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                restored_count = self._restore_categories(category_ids, request)

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Item Category",
                description=f"Bulk restored {restored_count} item categories",
                request=request,
                payload=payload,
            )

            return Response(
                {
                    "success": True,
                    "message": f"Successfully restored {restored_count} item category(ies).",
                    "data": {"restored_count": restored_count},
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _apply_archived_filters(self, queryset, request):
        """Apply filters to archived categories queryset"""
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        item_type_filter = request.query_params.get("allowed_item_type")
        if item_type_filter:
            queryset = queryset.filter(allowed_item_type=item_type_filter)

        return queryset

    @action(detail=False, methods=["get"], url_path="archived")
    def list_archived(self, request):
        """List all archived item categories"""
        try:
            queryset = (
                ItemCategory.objects.filter(is_archived=True)
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
        """Get archived item category details"""
        try:
            instance = (
                ItemCategory.objects.filter(id=pk, is_archived=True)
                .select_related("created_by", "updated_by")
                .first()
            )

            if not instance:
                return Response(
                    {"success": False, "message": "Archived item category not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class ItemCategoryArchiveViewSet(ModelViewSet):
    """
    ViewSet for Archived Item Categories (soft deleted)
    Read-only access to archived categories
    """

    queryset = (
        ItemCategory.objects.filter(is_archived=True)
        .select_related("created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = ItemCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]
    filterset_fields = ["status", "allowed_item_type"]
    search_fields = [
        "category_code",
        "category_name",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = ["category_name", "category_code", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]  # Read-only - only GET for list/retrieve

    def get_queryset(self):
        """Filter archived categories"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived item categories with pagination"""
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
        """Retrieve a single archived item category"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
