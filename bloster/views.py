import csv
import json
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
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from utils.aws_file_upload import delete_uploaded_bloster_file
from utils.custom_filters import CustomSearchFilter
from utils.error_handling import custom_exception
from utils.export_excel import ExportUtility
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from .models import BlosterMaster, BlosterType
from .serializers import (
    BlosterMasterDropdownSerializer,
    BlosterMasterSerializer,
    BlosterTypeSerializer,
)
from django.db.models import Count, Prefetch
from die.models import DieTool

logger = logging.getLogger(__name__)


class BlosterMasterViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = (
        BlosterMaster.objects.filter(deleted=False)
        .select_related("press", "type", "updated_by", "deleted_by")
        .order_by("-id")
    )
    serializer_class = BlosterMasterSerializer
    fy_filtering_enabled = False

    search_fields = BaseModelViewSet.serching_fields + [
        "id",
        "bloster_no",
        "press__name",
    ]

    ordering_fields = ["id", "bloster_no", "press__name"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        total_die_tool_count = 0
        total_die_ids = set()

        for bloster in queryset:
            first_tools = bloster.dietool_bloster_first.select_related("die")
            second_tools = bloster.dietool_bloster_second.select_related("die")
            third_tools = bloster.dietool_bloster_third.select_related("die")
            tools = list(first_tools) + list(second_tools) + list(third_tools)
            total_die_tool_count += len(tools)
            total_die_ids.update(dt.die.id for dt in tools if dt.die)

        total_die_count = len(total_die_ids)

        def get_nested_value(data, nested_key):
            try:
                for key in nested_key.split("__"):
                    if isinstance(data, dict):
                        data = data.get(key)
                    else:
                        return None
                return data
            except Exception:
                return None

        fields_param = request.query_params.get("fields")
        requested_fields = None
        if fields_param and fields_param.strip():
            requested_fields = [f.strip() for f in fields_param.split(",") if f.strip()]

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data

            if requested_fields:
                data = [
                    {field: get_nested_value(item, field) for field in requested_fields}
                    for item in data
                ]

            paginated_response = self.get_paginated_response(
                {
                    "success": True,
                    "data": data,
                }
            )
            paginated_response.data["total_die_tool_count"] = total_die_tool_count
            paginated_response.data["total_die_count"] = total_die_count
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        if requested_fields:
            data = [
                {field: get_nested_value(item, field) for field in requested_fields}
                for item in data
            ]

        return Response(
            {
                "success": True,
                "data": data,
                "total_die_tool_count": total_die_tool_count,
                "total_die_count": total_die_count,
            }
        )

    def get_queryset(self):
        queryset = (
            BlosterMaster.objects.filter(deleted=False)
            .select_related(
                "press",
                "type",
                "created_by",
                "updated_by",
                "deleted_by",
            )
            .prefetch_related(
                Prefetch(
                    "dietool_bloster_first",
                    queryset=DieTool.objects.select_related("die"),
                ),
                Prefetch(
                    "dietool_bloster_second",
                    queryset=DieTool.objects.select_related("die"),
                ),
                Prefetch(
                    "dietool_bloster_third",
                    queryset=DieTool.objects.select_related("die"),
                ),
            )
            .annotate(
                first_count=Count("dietool_bloster_first", distinct=True),
                second_count=Count("dietool_bloster_second", distinct=True),
                third_count=Count("dietool_bloster_third", distinct=True),
            )
        )

        id = self.request.query_params.get("id")
        deleted = self.request.query_params.get("deleted", False)

        filters = {"deleted": deleted}

        if id:
            filters["id"] = id

        return queryset.filter(**filters)

    def create(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])
        data["created_at"] = timezone.now()
        data["updated_at"] = None
        data["approved_at"] = None

        bloster_image = request.data.get("bloster_image", None)
        autocard = request.data.get("autocard", None)
        pdf = request.data.get("pdf", None)

        serializer = self.serializer_class(data=data)

        try:
            if serializer.is_valid():

                bloster = serializer.save(created_by=request.user)
                try:
                    bloster.upload_doc([bloster_image, autocard, pdf])
                except Exception as upload_error:
                    return Response(
                        {"success": False, "message": str(upload_error)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="Bolster",
                    description=f"Created Bolster '{getattr(bloster, 'bloster_no')}'.",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )

            else:
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return custom_exception(str(e))

    def update(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])

        data["updated_at"] = timezone.now()
        data["approved_at"] = None

        bloster_image = request.data.get("bloster_image", None)
        autocard = request.data.get("autocard", None)
        pdf = request.data.get("pdf", None)

        try:
            instance = self.get_object()
            serializer = self.serializer_class(instance, data=data, partial=True)

            if serializer.is_valid():
                bloster = serializer.save(updated_by=request.user)
                try:
                    bloster.upload_doc([bloster_image, autocard, pdf])
                except Exception as upload_error:
                    return Response(
                        {"success": False, "message": str(upload_error)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="Bolster",
                    description=f"Bolster '{getattr(bloster, 'bloster_no')}' updated.",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )

            else:
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = BlosterMaster.objects.filter(deleted=False)

        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = queryset.filter(bloster_no__icontains=filter_param)

        serializer = BlosterMasterDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def _validate_bulk_request(self, request):
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

    def _archive_blosters(self, bloster_ids, user):
        blosters = BlosterMaster.objects.filter(id__in=bloster_ids, deleted=False)

        if not blosters.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No active blosters found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        archived_names = list(blosters.values_list("bloster_no", flat=True))
        updated_count = blosters.update(
            deleted=True, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, archived_names, None

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        try:
            bloster_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, archived_names, error_response = self._archive_blosters(
                    bloster_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="DELETE",
                    module_name="BlosterMaster",
                    description=f"Archived {updated_count} bloster(s): {', '.join(archived_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} bloster(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def _restore_blosters(self, bloster_ids, user):
        blosters = BlosterMaster.objects.filter(id__in=bloster_ids, deleted=True)

        if not blosters.exists():
            return (
                None,
                None,
                Response(
                    {
                        "success": False,
                        "message": "No archived blosters found for the given IDs",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restored_names = list(blosters.values_list("bloster_no", flat=True))
        updated_count = blosters.update(
            deleted=False, updated_by=user, updated_at=timezone.now()
        )

        return updated_count, restored_names, None

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        try:
            bloster_ids, error_response = self._validate_bulk_request(request)
            if error_response:
                return error_response

            with transaction.atomic():
                updated_count, restored_names, error_response = self._restore_blosters(
                    bloster_ids, request.user
                )
                if error_response:
                    return error_response

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="RESTORE",
                    module_name="BlosterMaster",
                    description=f"Restored {updated_count} bloster(s): {', '.join(restored_names)}",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} bloster(s) restored successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(methods=["post"], detail=True, url_path="unarchive")
    def unarchive(self, request, pk=None):
        try:
            instance = BlosterMaster.objects.get(pk=pk, deleted=True)
        except BlosterMaster.DoesNotExist:
            return Response(
                {"success": False, "message": "Archived bloster not found."},
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
            module_name="BlosterMaster",
            description=f"Unarchived bloster '{getattr(instance, 'bloster_no', instance.id)}'",
            request=request,
            payload=clean_payload(request.data),
        )

        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Bloster unarchived successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def _parse_dry_run_param(self, dry_run_param):
        if isinstance(dry_run_param, str):
            return dry_run_param.lower() in ("true", "1", "yes")
        return bool(dry_run_param)

    def _format_import_log(self, log):
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
        logger.info(
            "Bulk import started",
            extra={
                "module": "BlosterMaster",
                "file_name": file.name,
                "file_size": file.size,
                "dry_run": dry_run,
                "user_id": user_id,
            },
        )

    def _log_import_complete(self, result):
        logger.info(
            "Bulk import completed",
            extra={
                "module": "BlosterMaster",
                "total_rows": result.get("total_rows", 0),
                "success_count": result.get("success_count", 0),
                "error_count": result.get("error_count", 0),
            },
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))
        self._log_import_start(file, dry_run, request.user.id)

        try:
            if hasattr(file, "seek"):
                file.seek(0)

            from imports.services.bloster_importer import BlosterImporter

            importer = BlosterImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            self._log_import_complete(result)

            return self._format_import_response(result, is_success=True)
        except Exception as e:
            return self._handle_import_exception(e, request)

    def _validate_import_file(self, request):
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
        logger.error(
            "Bulk import error",
            extra={
                "module": "BlosterMaster",
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

    def _format_error_row(self, row):
        return {
            "row_number": row.row_number,
            "error_type": row.error_type,
            "field_name": row.field_name,
            "error_message": row.error_message,
            "raw_data": row.raw_data,
        }

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        from imports.models import ImportLog

        logs = (
            ImportLog.objects.filter(module_name="BlosterMaster")
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

    @action(detail=True, methods=["get"], url_path="import-errors")
    def import_errors(self, request, pk=None):
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.select_related("created_by").get(
                id=pk, module_name="BlosterMaster"
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
        from imports.models import ImportErrorRow, ImportLog

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="BlosterMaster")
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
            f'attachment; filename="bloster_import_errors_{import_log_id}.csv"'
        )
        return response
    
    
    @action(detail=False, methods=["GET"], url_path="export-excel")
    def export_excel(self, request):

        queryset = self.get_queryset().filter(deleted=False).values(
                "bloster_no",
                "bloster_image",
                "press__name",
                "type__name",
                "diameter_mm",
                "thickness_mm",
                "size",
                "description",
                "autocard",
                "type__name",
                "pdf",
                "created_at",
                "created_by__full_name",
                "updated_at",
                "updated_by__full_name",
                )
       
        columns = [
                    ("Sr. No.", "sr_no"),
                    ("Bloster No", "bloster_no"),
                    ("Bloster Image", "bloster_image"),
                    ("Press", "press__name"),
                    ("Type", "type__name"),
                    ("Diameter MM", "diameter_mm"),
                    ("Thickness MM", "thickness_mm"),
                    ("Size", "size"),
                    ("Description", "description"),
                    ("Autocard", "autocard"),
                    ("PDF", "pdf"),
                    ("Created At", "created_at"),
                    ("Created By", "created_by__full_name"),
                    ("Updated At", "updated_at"),
                    ("Updated By", "updated_by__full_name"),
                ]

        return ExportUtility.export_excel(
                queryset=queryset,
                columns=columns,
                filename="bloster.xlsx",
                sheet_name="Bloster",
            )


class DeleteBlosterUploadedFile(ModelViewSet):
    queryset = BlosterMaster.objects.all().order_by("-id")
    serializer_class = BlosterMasterSerializer
    filter_backends = [CustomSearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        fields_to_update = {
            "bloster_image": request.data.get("bloster_image"),
            "autocard": request.data.get("autocard"),
            "pdf": request.data.get("pdf"),
        }
        deleted_fields = []

        for field, provided_url in fields_to_update.items():
            if provided_url is not None:
                file_exists = delete_uploaded_bloster_file(provided_url)
                if not file_exists:
                    return Response(
                        {"error": f"File for {field} does not exist in S3."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                setattr(instance, field, None)

                instance.save()
                deleted_fields.append(field)

        if not deleted_fields:
            return Response(
                {"error": "No valid fields provided for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.save()

        return Response(
            {
                "message": "Selected file(s) deleted successfully.",
                "deleted_fields": deleted_fields,
            },
            status=status.HTTP_200_OK,
        )


class BlosterMasterArchiveViewSet(ArchiveMixin):
    queryset = (
        BlosterMaster.objects.filter(deleted=True)
        .select_related("press", "created_by", "updated_by", "deleted_by")
        .order_by("-updated_at")
    )
    serializer_class = BlosterMasterSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = [
        "bloster_no",
        "press__name",
        "created_by__first_name",
        "created_by__last_name",
    ]
    ordering_fields = ["bloster_no", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

    def list(self, request, *args, **kwargs):
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
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)


class BlosterTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = BlosterType.objects.all()
    serializer_class = BlosterTypeSerializer
