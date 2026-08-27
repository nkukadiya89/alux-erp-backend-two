import logging

from django.forms import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from common.master_views import BaseModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from common.models import ArchiveMixin
from die.models import Die, DieTool, DieToolBrokenImage
from die.serializers import DieToolSerializers
from imports.models import ImportErrorRow, ImportLog
from imports.services.dietool_importer import DieToolImporter
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from django.db import transaction
import json

logger = logging.getLogger("file")


class DieToolViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        DieTool.objects.select_related(
            "die",
            "die_size",
            "customer",
            "eligible_for_press",
            "created_by",
            "updated_by",
        ).prefetch_related("first_bloster", "second_bloster", "third_bloster")
        .order_by("-created_at")
    )
    serializer_class = DieToolSerializers
    # Keep DjangoFilterBackend AND inherit Search/Ordering (override was dropping SearchFilter)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ["die"]

    search_fields = [
        "id",
        "die__die_number",          # Section No
        "tool_number",              # Die No
        "drawing_no",               # Drawing No
        "die_oblique_number",       # Die Oblique No
        "die__die_group__name",
        "developer_ref_no",
        "die_size__diameter",       # Die Size (renamed from die_height)
        "die_size__thickness",
        "die_cavity",
        "customer__customer_name",
        "customer__code",
        "eligible_for_press__name",
        "received_date",
        "order_date",
        "first_bloster__bloster_no",
        "second_bloster__bloster_no",
        "third_bloster__bloster_no",
        "purchase_price",
        "tool_status",
        "tool_status_reason",
        "ownership",
        "remarks",
        "rac_no",
        "row_no",
        "column_no",
        "die_location",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "die_option",
        "thickness",
        "diameter",
        "backer_number",
        "actual_kg",
        "drawing_kg",
        "status",
        "location",
        "feeder_number",
    ]

    ordering_fields = [
        "id",
        "die__die_number",
        "die__die_group__name",
        "developer_ref_no",
        "tool_number",
        "die_size__diameter",
        "die_size__thickness",
        "die_cavity",
        "eligible_for_press__name",
        "received_date",
        "order_date",
        "total_running_kg",
        "purchase_price",
        "tool_status",
        "ownership",
        "is_active",
        "remarks",
        "drawing_no",
        "die_oblique_number",
        "rac_no",
        "row_no",
        "column_no",
        "die_location",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "die_option",
        "thickness",
        "diameter",
        "backer_number",
        "actual_kg",
        "status",
        "location",
        "created_at",
    ]

    @transaction.atomic
    def create(self, request, *args, **kwargs):

        data = json.loads(request.data["form_data"])

        data["created_at"] = timezone.now()
        data["updated_at"] = None
        serializer = self.serializer_class(data=data)

        try:
            if not serializer.is_valid():
                print(serializer.errors)
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if serializer.is_valid():
                instance = serializer.save(created_by=request.user)
                images = request.FILES.getlist("die_broken_images")

                try:
                    DieToolBrokenImage.upload_doc(instance, images)
                except Exception as upload_error:
                    return Response(
                        {"success": False, "message": upload_error.message_dict if hasattr(upload_error, 'message_dict') else str(upload_error)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="Profile Tool",
                    description=f"Created Profile Tool (ID: {instance.id})",
                    request=request,
                    payload=payload,
                )

                response_serializer = (self.get_serializer(instance))

                return Response({"success": True, "data": response_serializer.data}, status=status.HTTP_201_CREATED)
            else:
                return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return custom_exception(str(e))

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if "form_data" in request.data:
            data = json.loads(request.data["form_data"])
        else:
            data = request.data.copy()
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True)

            if not serializer.is_valid():
                logger.error(f"Error in updating record: {serializer.errors}")
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save(updated_by=request.user)

            images = request.FILES.getlist("die_broken_images")
            existing_count = instance.die_broken_images.count()
            total_count = existing_count + len(images)

            if total_count > 4:
                raise ValidationError({"die_broken_images": "Maximum 4 images allowed."})

            for image in images:
                try:
                    DieToolBrokenImage.upload_doc(instance, images)
                except Exception as upload_error:
                    return Response(
                        {
                            "success": False,
                            "message": upload_error.message_dict
                            if hasattr(upload_error, 'message_dict')
                            else str(upload_error)
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Profile Tool",
                description=f"Updated Profile Tool (ID: {instance.id})",
                request=request,
                payload=payload,
            )
            logger.info("Record updated successfully.")

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            return custom_exception(e)

    @action(
        detail=False, methods=["GET"], url_path=r"(?P<die_id>\d+)/die-tool-by-profile"
    )
    def die_tool_by_profile(self, request, die_id=None):
        """
        API to get a list of Die Tools filtered by Die ID.
        """
        die_tools = DieTool.objects.filter(die_id=die_id)

        serializer = self.get_serializer(die_tools, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
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

    def _format_error_row(self, row):
        return {
            "row_number": row.row_number,
            "error_type": row.error_type,
            "field_name": row.field_name,
            "error_message": row.error_message,
            "raw_data": row.raw_data,
        }

    def _build_error_summary(self, error_rows):
        summary = {"total_errors": error_rows.count(), "error_types": {}}
        for row in error_rows:
            summary["error_types"][row.error_type] = summary["error_types"].get(row.error_type, 0) + 1
        return summary

    def _format_import_response(self, result, is_success, error_message=None, error_status_code=status.HTTP_400_BAD_REQUEST):
        if is_success and result:
            data = result.get("data", {})
            row_errors = data.get("row_errors", [])
            # Build a flat, readable errors list grouped by row
            errors = [
                {
                    "row": e.get("row_number"),
                    "errors": [
                        f"{err.get('field', 'unknown')}: {err.get('message', '')}"
                        + (f" (value: {err['value']}" + ")" if err.get("value") else "")
                        for err in (e.get("errors") or [])
                    ],
                }
                for e in row_errors
            ]
            return Response(
                {
                    "success": result.get("success", True),
                    "message": result.get("message", "Import completed successfully"),
                    "data": {
                        "total_records": data.get("total_records", 0),
                        "inserted": data.get("inserted", 0),
                        "updated": data.get("updated", 0),
                        "skipped": data.get("skipped", 0),
                        "failed": data.get("failed", 0),
                        "success_count": data.get("success_count", 0),
                        "error_count": data.get("error_count", 0),
                        "import_log_id": data.get("import_log_id", ""),
                    },
                    "errors": errors,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": error_message or "Import failed"},
            status=error_status_code,
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        if "file" not in request.FILES:
            return Response(
                {"success": False, "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file = request.FILES["file"]
        dry_run = self._parse_dry_run_param(request.data.get("dry_run", False))

        try:
            if hasattr(file, "seek"):
                file.seek(0)
            importer = DieToolImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            return self._format_import_response(result, is_success=True)
        except Exception as e:
            logger.error(f"Error in DieTool bulk import: {str(e)}", exc_info=True)
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        logs = (
            ImportLog.objects.filter(module_name="DieTool")
            .select_related("created_by")
            .order_by("-started_at")
        )
        page = self.paginate_queryset(logs)
        if page is not None:
            data = [self._format_import_log(log) for log in page]
            return self.get_paginated_response({"success": True, "data": data})
        return Response({"success": True, "data": [self._format_import_log(log) for log in logs]}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="import-errors")
    def import_errors(self, request, pk=None):
        try:
            import_log = ImportLog.objects.select_related("created_by").get(id=pk, module_name="DieTool")
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        error_rows = ImportErrorRow.objects.filter(import_log=import_log).order_by("row_number")
        return Response(
            {"success": True, "data": {"summary": self._build_error_summary(error_rows), "errors": [self._format_error_row(r) for r in error_rows]}},
            status=status.HTTP_200_OK,
        )


class GetDieToolDetials(ArchiveMixin):
    queryset = DieTool.objects.all().order_by("-id")

    def list(self, request, *args, **kwargs):
        data = request.query_params

        die_number = data.get("die")

        total_running_qty = 0.0
        total_running_ton = 0.0

        die_tool_count = DieTool.objects.filter(die__die_number=die_number).count()

        try:
            die = Die.objects.get(die_number=die_number)
            die_type = die.die_type

        except Die.DoesNotExist:
            return Response(
                {"success": False, "message": "Die not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        tool_number = f"{die_tool_count + 1}"
        return Response(
            {
                "success": True,
                "data": {
                    "total_running_qty": total_running_qty,
                    "total_running_ton": total_running_ton,
                    "tool_number": tool_number,
                    "die_type": die_type,
                    "wt_kg_p_mt": die.wt_kg_p_mt if tool_number == "1" else 0.0,
                },
            }
        )
