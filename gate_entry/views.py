import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.master_views import BaseModelViewSet
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

from .models import GateEntry
from .serializers import (
    GateEntryDetailSerializer,
    GateEntryDropdownSerializer,
    GateEntryListSerializer,
    GateEntryWriteSerializer,
)
from .services import (
    bulk_archive_gate_entries,
    bulk_restore_gate_entries,
    close_gate_entry,
    create_gate_entry,
    update_gate_entry,
)

logger = logging.getLogger("file")


def _get_base_queryset():
    return (
        GateEntry.objects.filter(deleted=False)
        .select_related("vendor", "transporter", "created_by", "updated_by")
        .annotate(items_count=Count("items"))
        .prefetch_related("items")
        .order_by("-date", "-created_at")
    )


class GateEntryViewSet(BaseModelViewSet):
    """
    CRUD and custom actions for Gate Entry.
    APIs: list, create, retrieve, update, partial_update, destroy,
    change-status, close, dropdown, next-number, bulk-archive, bulk-restore.
    """

    queryset = _get_base_queryset()
    serializer_class = GateEntryWriteSerializer
    list_serializer_class = GateEntryListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "status",
        "vendor",
        "transporter",
        "date",
        "vehicle_no",
        "gate_entry_no",
        "driver_name",
    ]
    search_fields = [
        "gate_entry_no",
        "driver_name",
        "vehicle_no",
        "challan_no",
        "invoice_no",
        "vendor__person_name",
        "vendor__vendor_registered_name",
        "transporter__party_name",
    ]
    ordering_fields = [
        "gate_entry_no",
        "date",
        "inward_time",
        "outward_time",
        "status",
        "created_at",
        "updated_at",
    ]
    ordering = ["-date", "-created_at"]
    fy_filtering_enabled = False

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        if self.action in ("create", "update", "partial_update"):
            return GateEntryWriteSerializer
        return GateEntryDetailSerializer

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(
                page if page is not None else queryset, many=True
            )
            response_data = {"success": True, "data": serializer.data}
            if page is not None:
                return self.get_paginated_response(response_data)
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Gate entry list failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Gate entry retrieve failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            from utils.generate_number import generate_gate_entry_no

            data = request.data.copy()
            if not data.get("gate_entry_no"):
                data["gate_entry_no"] = generate_gate_entry_no()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(data=data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="GateEntry",
                description=f"Created gate entry '{instance.gate_entry_no}'",
                request=request,
                payload=payload,
            )
            out_serializer = GateEntryDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except DjangoValidationError as e:
            msg = str(e.message_list[0]) if getattr(e, "message_list", None) else str(e)
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Gate entry create failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(
                instance, data=request.data, partial=False, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="GateEntry",
                description=f"Updated gate entry '{instance.gate_entry_no}'",
                request=request,
                payload=payload,
            )
            instance.refresh_from_db()
            out_serializer = GateEntryDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except DjangoValidationError as e:
            msg = str(e.message_list[0]) if getattr(e, "message_list", None) else str(e)
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Gate entry update failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(
                instance, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="GateEntry",
                description=f"Updated gate entry '{instance.gate_entry_no}'",
                request=request,
                payload=payload,
            )
            instance.refresh_from_db()
            out_serializer = GateEntryDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except DjangoValidationError as e:
            msg = str(e.message_list[0]) if getattr(e, "message_list", None) else str(e)
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Gate entry partial_update failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.status == GateEntry.STATUS_CLOSE:
                return Response(
                    {
                        "success": False,
                        "message": "Closed gate entry cannot be deleted.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.deleted = True
            instance.updated_by = request.user
            instance.updated_at = timezone.now()
            instance.save(update_fields=["deleted", "updated_by", "updated_at"])

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="GateEntry",
                description=f"Deleted gate entry '{instance.gate_entry_no}'",
                request=request,
                payload=None,
            )

            return Response(
                {"success": True, "message": "Gate entry deleted successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Gate entry destroy failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Change status (in_company / close). Validates outward_time and empty_vehicle_weight when closing."""
        try:
            instance = get_object_or_404(GateEntry, pk=pk, deleted=False)
            new_status = (request.data.get("status") or "").strip().lower()

            if new_status not in [GateEntry.STATUS_IN_COMPANY, GateEntry.STATUS_CLOSE]:
                return Response(
                    {
                        "success": False,
                        "message": "Status must be 'in_company' or 'close'.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if instance.status == new_status:
                return Response(
                    {
                        "success": False,
                        "message": f"Gate entry is already {new_status.replace('_', ' ')}.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_status == GateEntry.STATUS_CLOSE:
                updated = close_gate_entry(
                    instance,
                    request.user,
                    outward_time=request.data.get("outward_time"),
                    empty_vehicle_weight=request.data.get("empty_vehicle_weight"),
                )
            else:
                instance.status = new_status
                instance.updated_by = request.user
                instance.updated_at = timezone.now()
                instance.save(update_fields=["status", "updated_by", "updated_at"])
                updated = instance

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="GateEntry",
                description=f"Changed gate entry status to '{new_status}' for '{updated.gate_entry_no}'",
                request=request,
                payload=clean_payload(request.data),
            )
            serializer = GateEntryDetailSerializer(updated)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except DjangoValidationError as e:
            msg = str(e.message_list[0]) if getattr(e, "message_list", None) else str(e)
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Gate entry change_status failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """Close gate entry. Requires outward_time and empty_vehicle_weight in body."""
        try:
            instance = get_object_or_404(GateEntry, pk=pk, deleted=False)
            updated = close_gate_entry(
                instance,
                request.user,
                outward_time=request.data.get("outward_time"),
                empty_vehicle_weight=request.data.get("empty_vehicle_weight"),
            )
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="GateEntry",
                description=f"Closed gate entry '{updated.gate_entry_no}'",
                request=request,
                payload=clean_payload(request.data),
            )
            serializer = GateEntryDetailSerializer(updated)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "message": "Gate entry closed.",
                },
                status=status.HTTP_200_OK,
            )
        except DjangoValidationError as e:
            msg = str(e.message_list[0]) if getattr(e, "message_list", None) else str(e)
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Gate entry close failed: %s", e)
            return custom_exception(e)



    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown; excludes archived."""
        queryset = (
            self.get_queryset()
            .filter(is_archived=False)
            .only("id", "gate_entry_no", "date", "status", "vehicle_no")
        )
        serializer = GateEntryDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="next-number")
    def next_number(self, request):
        """Return next gate entry number for the form."""
        try:
            from utils.generate_number import generate_gate_entry_no

            next_no = generate_gate_entry_no()
            return Response(
                {"success": True, "data": {"gate_entry_no": next_no}},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Gate entry next_number failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = bulk_archive_gate_entries(ids, request.user)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} gate entry(ies) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Gate entry bulk_archive failed: %s", e)
            return custom_exception(e)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = bulk_restore_gate_entries(ids, request.user)
            qs = self.get_queryset().filter(id__in=ids)
            serializer = GateEntryListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} gate entry(ies) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Gate entry bulk_restore failed: %s", e)
            return custom_exception(e)

    def _validate_import_file(self, request):
        if "file" not in request.FILES:
            return None, Response(
                {"success": False, "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return request.FILES["file"], None

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Bulk import Gate Entry (stub; implement importer as per Gate Pass)."""
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response
        return Response(
            {
                "success": False,
                "message": "Gate entry bulk import not yet implemented. Use Gate Pass importer as reference.",
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Gate Entry module."""
        from imports.models import ImportLog

        logs = ImportLog.objects.filter(module_name="GateEntry").order_by("-started_at")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size
        logs_page = logs[start:end]
        data = [
            {
                "id": str(log.id),
                "file_name": log.file_name,
                "status": log.status,
                "total_rows": log.total_rows,
                "success_count": log.success_count,
                "error_count": log.error_count,
                "success_rate": getattr(log, "success_rate", None),
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": (
                    log.completed_at.isoformat() if log.completed_at else None
                ),
            }
            for log in logs_page
        ]
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
        """Get errors for a specific Gate Entry import log (pk = import_log_id)."""
        from imports.models import ImportLog
        from imports.reports.error_report import ErrorReport

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="GateEntry")
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        report = ErrorReport(import_log)
        errors = report.get_error_rows()
        summary = report.get_errors_summary()
        return Response(
            {"success": True, "data": {"summary": summary, "errors": errors}},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="download-error-report")
    def download_error_report(self, request, pk=None):
        """Download error report CSV for import log (pk = import_log_id)."""
        from django.http import HttpResponse
        from imports.models import ImportLog
        from imports.reports.error_report import ErrorReport

        try:
            import_log = ImportLog.objects.get(id=pk, module_name="GateEntry")
        except ImportLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Import log not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        report = ErrorReport(import_log)
        csv_content = report.generate_csv_report()
        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="gate_entry_import_errors_{pk}.csv"'
        )
        return response


class GateEntryArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for archived gate entries. Consistent response format."""

    queryset = (
        GateEntry.objects.filter(deleted=False, is_archived=True)
        .select_related("vendor", "transporter", "created_by", "updated_by")
        .annotate(items_count=Count("items"))
        .prefetch_related("items")
        .order_by("-updated_at")
    )
    serializer_class = GateEntryListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "status",
        "vendor",
        "transporter",
        "date",
        "vehicle_no",
        "gate_entry_no",
        "driver_name",
    ]
    search_fields = [
        "gate_entry_no",
        "driver_name",
        "vehicle_no",
        "challan_no",
        "invoice_no",
        "vendor__person_name",
        "transporter__party_name",
    ]
    ordering_fields = [
        "gate_entry_no",
        "date",
        "created_at",
        "updated_at",
        "status",
    ]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GateEntryDetailSerializer
        return GateEntryListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset, many=True
        )
        if page is not None:
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )
