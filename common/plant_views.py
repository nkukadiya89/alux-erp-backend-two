import logging

from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.models import Plant
from common.serializers import PlantDropdownSerializer, PlantSerializer
from common.services.plant_service import can_deactivate_plant, can_delete_plant
from imports.models import ImportErrorRow, ImportLog
from imports.services.plant_importer import PlantImporter
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class PlantViewSet(ModelViewSet):
    queryset = (
        Plant.objects.filter(deleted=False)
        .select_related("plant_type", "plant_head", "created_by", "updated_by")
        .order_by("-created_at")
    )
    serializer_class = PlantSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    fy_filtering_enabled = False
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "plant_type"]
    search_fields = [
        "plant_code",
        "plant_type__name",
        "plant_name",
        "city",
        "status",
        "address_line_1",
        "address_line_2",
        "city",
        "state",
        "country",
        "postal_code",
        "phone_number",
        "email",
    ]
    ordering_fields = [
        "plant_name",
        "plant_type",
        "city",
        "plant_code",
        "status",
        "address_line_1",
        "address_line_2",
        "city",
        "state",
        "country",
        "postal_code",
        "phone_number",
        "email",
        "plant_head",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by deleted=False by default
        return queryset.filter(deleted=False)

    def get_serializer_class(self):
        """Use full serializer for all operations"""
        return PlantSerializer

    def list(self, request, *args, **kwargs):
        """List all plants with pagination, filtering, and search - returns all fields"""
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
        """Retrieve a single plant detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Create a new plant"""
        try:
            # Explicit uniqueness check for plant_code
            plant_code = request.data.get("plant_code")
            if plant_code:
                plant_code = plant_code.strip().upper()
                if Plant.objects.filter(plant_code__iexact=plant_code).exists():
                    return Response(
                        {
                            "success": False,
                            "message": f"Plant with code '{plant_code}' already exists.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(created_by=request.user, updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Plant",
                description=f"Created plant '{instance.plant_code} - {instance.plant_name}'",
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
        """Update a plant (full update)"""
        try:
            instance = self.get_object()

            # Explicit uniqueness check for plant_code
            plant_code = request.data.get("plant_code")
            if plant_code:
                plant_code = plant_code.strip().upper()
                if (
                    Plant.objects.filter(plant_code__iexact=plant_code)
                    .exclude(pk=instance.pk)
                    .exists()
                ):
                    return Response(
                        {
                            "success": False,
                            "message": f"Plant with code '{plant_code}' already exists.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user, updated_at=timezone.now())

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Plant",
                description=f"Updated plant '{instance.plant_code} - {instance.plant_name}'",
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
        """Partial update a plant"""
        try:
            instance = self.get_object()

            # Explicit uniqueness check for plant_code if provided
            plant_code = request.data.get("plant_code")
            if plant_code:
                plant_code = plant_code.strip().upper()
                if (
                    Plant.objects.filter(plant_code__iexact=plant_code)
                    .exclude(pk=instance.pk)
                    .exists()
                ):
                    return Response(
                        {
                            "success": False,
                            "message": f"Plant with code '{plant_code}' already exists.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Plant",
                description=f"Updated plant '{instance.plant_code} - {instance.plant_name}'",
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
        """Soft delete a plant"""
        try:
            instance = self.get_object()

            can_delete, error_message = can_delete_plant(instance)
            if not can_delete:
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
                module_name="Plant",
                description=f"Deleted plant '{instance.plant_code} - {instance.plant_name}'",
                request=request,
                payload=None,
            )

            return Response(
                {"success": True, "message": "Plant deleted successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _validate_status_change(self, instance, new_status):
        """Validate status change request"""
        if new_status not in ["Active", "Inactive"]:
            return False, "Status must be 'Active' or 'Inactive'"

        if instance.status == new_status:
            return False, f"Plant is already {new_status}"

        if new_status == "Inactive":
            can_deactivate, error_message = can_deactivate_plant(instance)
            if not can_deactivate:
                return False, error_message

        return True, None

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change plant status (Active/Inactive)"""
        try:
            instance = self.get_object()
            new_status = request.data.get("status")

            is_valid, error_message = self._validate_status_change(instance, new_status)
            if not is_valid:
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.status = new_status
            instance.updated_by = request.user
            instance.updated_at = timezone.now()
            instance.save()

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Plant",
                description=f"Changed plant status to '{new_status}' for '{instance.plant_code} - {instance.plant_name}'",
                request=request,
                payload=payload,
            )

            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown API - returns only id, plant_code, plant_name"""
        queryset = self.get_queryset().filter(status="Active")
        serializer = PlantDropdownSerializer(queryset, many=True)
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

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import plants from Excel/CSV file"""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        logger.info(
            f"Bulk import - File: {file.name}, Size: {file.size}, Dry run: {dry_run}"
        )

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            importer = PlantImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            logger.info(f"Import completed - Success: {result.get('success')}")

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            logger.error(f"Error in bulk import: {str(e)}", exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(e),
                error_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        """Get import logs for Plant module"""
        logs = ImportLog.objects.filter(module_name="Plant").order_by("-started_at")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        logs_page = logs[start:end]
        data = [self._format_import_log(log) for log in logs_page]

        return Response(
            {
                "success": True,
                "data": data,
                "count": logs.count(),
                "page": page,
                "page_size": page_size,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="import-errors")
    def import_errors(self, request, pk=None):
        """
        Get errors for a specific import log.
        Note: pk here is import_log_id, not plant_id
        """
        try:
            import_log = ImportLog.objects.get(id=pk, module_name="Plant")
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # error_report = ErrorReport(import_log)
        # errors = error_report.get_error_rows()
        # summary = error_report.get_errors_summary()

        return Response(
            {"success": True, "data": {"summary": "summary", "errors": "errors"}},
            status=status.HTTP_200_OK,
        )

    def _validate_bulk_request(self, request):
        """Validate bulk request data"""
        plant_ids = request.data.get("ids", [])

        if not plant_ids:
            return None, Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(plant_ids, list):
            return None, Response(
                {
                    "success": False,
                    "message": "ids must be a list",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return plant_ids, None

    def _archive_plants(self, plant_ids, user):
        """Archive plants and return updated count and codes"""
        plants = Plant.objects.filter(id__in=plant_ids, deleted=False)

        if not plants.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active plants found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        # Validate each plant can be deleted
        for plant in plants:
            can_delete, error_message = can_delete_plant(plant)
            if not can_delete:
                return (
                    None,
                    None,
                    Response(
                        {
                            "success": False,
                            "message": f"Cannot archive plant '{plant.plant_code}': {error_message}",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    ),
                )

        archived_codes = list(plants.values_list("plant_code", flat=True))
        updated_count = plants.update(
            deleted=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        """Bulk archive (soft delete) plants"""
        try:
            plant_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_codes, error_response = self._archive_plants(
                    plant_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="Plant",
                    description=f"Archived {updated_count} plant(s): {', '.join(archived_codes)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} plant(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_plants(self, plant_ids, user):
        """Restore archived plants and return updated count and codes"""
        plants = Plant.objects.filter(id__in=plant_ids, deleted=True)

        if not plants.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived plants found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_codes = list(plants.values_list("plant_code", flat=True))
        updated_count = plants.update(
            deleted=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_codes, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        """Bulk restore archived plants"""
        try:
            plant_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_codes, error_response = self._restore_plants(
                    plant_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="Plant",
                    description=f"Restored {updated_count} plant(s): {', '.join(restored_codes)}",
                    request=request,
                    payload=payload,
                )

            restored_instances = Plant.objects.filter(id__in=plant_ids)
            serializer = self.get_serializer(restored_instances, many=True)

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} plant(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    # @action(detail=True, methods=["get"], url_path="download-error-report")
    # def download_error_report(self, request, pk=None):
    #     """
    #     Download error report as CSV.
    #     Note: pk here is import_log_id, not plant_id
    #     """
    #     try:
    #         import_log = ImportLog.objects.get(id=pk, module_name="Plant")
    #     except ImportLog.DoesNotExist:
    #         return Response(
    #             {"success": False, "message": "Import log not found"},
    #             status=status.HTTP_404_NOT_FOUND
    #         )

    #     # error_report = ErrorReport(import_log)
    #     # csv_content = error_report.generate_csv_report()

    #     from django.http import HttpResponse
    #     # response = HttpResponse(csv_content, content_type='text/csv')
    #     response['Content-Disposition'] = f'attachment; filename="plant_import_errors_{pk}.csv"'
    #     return response


class PlantArchiveViewSet(ModelViewSet):
    queryset = (
        Plant.objects.filter(deleted=True)
        .select_related("plant_type", "plant_head", "created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = PlantSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "plant_type"]
    search_fields = ["plant_code", "plant_name", "city"]
    ordering_fields = ["plant_name", "created_at", "plant_code", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]  # Read-only - only GET for list/retrieve

    def get_queryset(self):
        """Filter archived plants"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived plants with pagination"""
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
        """Retrieve a single archived plant"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
