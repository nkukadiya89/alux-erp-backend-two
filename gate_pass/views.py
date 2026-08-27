import logging

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
from imports.models import ImportLog

# from imports.reports.error_report import ErrorReport
from imports.services.gate_pass_importer import GatePassImporter
from utils.error_handling import custom_exception
from utils.pagination import Pagination

from .models import GatePass
from .permissions import IsGatePassCreatorOrReadOnly
from .serializers import (
    GatePassDetailSerializer,
    GatePassDropdownSerializer,
    GatePassListSerializer,
    GatePassPrintSerializer,
    GatePassWriteSerializer,
)
from .services import (
    bulk_archive_gate_passes,
    bulk_restore_gate_passes,
    load_po_items,
    mark_gate_pass_in_process,
    mark_gate_pass_returned,
    submit_gate_pass,
)

logger = logging.getLogger("file")


class GatePassViewSet(BaseModelViewSet):
    """
    CRUD and status actions for Gate Pass.
    APIs: list, create, retrieve, update, partial_update, destroy,
    submit, mark-in-process, mark-returned, dropdown, next-number,
    load-po-items, print-data, bulk-archive, bulk-restore,
    bulk-import, import-logs, import-errors, error-report/download.
    """

    queryset = GatePass.objects.filter(deleted=False).order_by("-date", "-created_at")
    serializer_class = GatePassWriteSerializer
    list_serializer_class = GatePassListSerializer
    permission_classes = [IsAuthenticated, IsGatePassCreatorOrReadOnly]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "type",
        "status",
        "vehicle_no",
        "gate_pass_no",
        "po_id",
        "party_name",
    ]
    search_fields = [
        "gate_pass_no",
        "vehicle_no",
        "party_name",
        "remarks",
    ]
    ordering_fields = [
        "date",
        "created_at",
        "updated_at",
        "gate_pass_no",
        "status",
    ]
    ordering = ["-date", "-created_at"]

    def get_queryset(self):
        qs = (
            GatePass.objects.filter(deleted=False)
            .select_related("created_by", "updated_by")
            .annotate(items_count=Count("items"))
            .prefetch_related("items")
            .order_by("-date", "-created_at")
        )
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
            return GatePassWriteSerializer
        if self.action == "print_data":
            return GatePassPrintSerializer
        return GatePassDetailSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        from utils.generate_number import generate_gate_pass_no

        data = request.data.copy()
        if not data.get("gate_pass_no"):
            data["gate_pass_no"] = generate_gate_pass_no()
        serializer = self.get_serializer(data=data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = GatePassDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.exception("Failed to create gate pass: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = GatePassDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Failed to update gate pass: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from .models import GatePass as GatePassModel

        if instance.status != GatePassModel.STATUS_DRAFT:
            return Response(
                {
                    "success": False,
                    "message": "Only draft gate passes can be deleted.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.deleted = True
        instance.deleted_at = timezone.now()
        instance.deleted_by = request.user
        instance.is_archived = True
        instance.save(
            update_fields=["deleted", "deleted_at", "deleted_by", "is_archived"]
        )
        return Response(
            {"success": True, "message": "Gate pass deleted successfully."},
            status=status.HTTP_200_OK,
        )

    def _validate_import_file(self, request):
        if "file" not in request.FILES:
            return None, Response(
                {"success": False, "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return request.FILES["file"], None

    def _parse_dry_run(self, value):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    def _format_import_response(
        self,
        result,
        is_success: bool,
        error_message: str | None = None,
        error_status: int = status.HTTP_400_BAD_REQUEST,
    ):
        if is_success and result:
            return Response(
                {
                    "success": True,
                    "message": result.get(
                        "message", "Gate Pass import completed successfully"
                    ),
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
        return Response(
            {
                "success": False,
                "message": error_message or "Import failed",
            },
            status=error_status,
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """
        Bulk import Gate Pass headers from CSV/Excel.
        """
        file, error_response = self._validate_import_file(request)
        if error_response:
            return error_response

        dry_run = self._parse_dry_run(request.data.get("dry_run", False))
        logger.info(
            "GatePass bulk import - File: %s, Size: %s, Dry run: %s",
            getattr(file, "name", ""),
            getattr(file, "size", 0),
            dry_run,
        )

        try:
            importer = GatePassImporter(file, user=request.user, dry_run=dry_run)
            result = importer.import_data()
            return self._format_import_response(
                result, is_success=result.get("success")
            )
        except Exception as exc:
            logger.error("GatePass bulk import error: %s", exc, exc_info=True)
            return self._format_import_response(
                None,
                is_success=False,
                error_message=str(exc),
                error_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        gate_pass = get_object_or_404(GatePass, pk=pk, deleted=False)
        self.check_object_permissions(request, gate_pass)
        try:
            updated = submit_gate_pass(gate_pass, request.user)
            data = GatePassDetailSerializer(updated).data
            return Response(
                {"success": True, "data": data, "message": "Submitted successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Failed to submit gate pass %s: %s", gate_pass.id, exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="mark-in-process")
    def mark_in_process(self, request, pk=None):
        gate_pass = get_object_or_404(GatePass, pk=pk, deleted=False)
        self.check_object_permissions(request, gate_pass)
        try:
            updated = mark_gate_pass_in_process(gate_pass, request.user)
            data = GatePassDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Marked as IN_PROCESS.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception(
                "Failed to mark gate pass %s in process: %s", gate_pass.id, exc
            )
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="mark-returned")
    def mark_returned(self, request, pk=None):
        gate_pass = get_object_or_404(GatePass, pk=pk, deleted=False)
        self.check_object_permissions(request, gate_pass)
        try:
            updated = mark_gate_pass_returned(gate_pass, request.user)
            data = GatePassDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Marked as returned.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception(
                "Failed to mark gate pass %s returned: %s", gate_pass.id, exc
            )
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        """Lightweight dropdown; excludes archived."""
        qs = (
            self.get_queryset()
            .filter(is_archived=False)
            .only("id", "gate_pass_no", "type", "status", "date", "party_name")
        )
        serializer = GatePassDropdownSerializer(qs, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="next-number")
    def next_number(self, request):
        """Return next gate pass number for the form."""
        try:
            from utils.generate_number import generate_gate_pass_no

            next_no = generate_gate_pass_no()
            return Response(
                {"success": True, "data": {"gate_pass_no": next_no}},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Gate pass next_number failed: %s", exc)
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request):
        """Get import logs for Gate Pass module with pagination."""
        logs = ImportLog.objects.filter(module_name="GatePass").order_by("-started_at")
        page = self.paginate_queryset(logs)
        if page is not None:
            data = [
                {
                    "id": str(log.id),
                    "file_name": log.file_name,
                    "status": log.status,
                    "total_rows": log.total_rows,
                    "success_count": log.success_count,
                    "error_count": log.error_count,
                    "success_rate": getattr(log, "success_rate", None),
                    "started_at": (
                        log.started_at.isoformat() if log.started_at else None
                    ),
                    "completed_at": (
                        log.completed_at.isoformat() if log.completed_at else None
                    ),
                }
                for log in page
            ]
            return self.get_paginated_response({"success": True, "data": data})
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
            for log in logs
        ]
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )

    # @action(detail=True, methods=["get"], url_path="import-errors")
    # def import_errors(self, request, pk=None):
    #     """
    #     Get errors for a specific Gate Pass import log.

    #     Note: pk here is import_log_id, not gate_pass_id.
    #     """
    #     try:
    #         import_log = ImportLog.objects.get(id=pk, module_name="GatePass")
    #     except ImportLog.DoesNotExist:
    #         return Response(
    #             {"success": False, "message": "Import log not found"},
    #             status=status.HTTP_404_NOT_FOUND,
    #         )

    #     # report = ErrorReport(import_log)
    #     errors = report.get_error_rows()
    #     summary = report.get_errors_summary()
    #     return Response(
    #         {"success": True, "data": {"summary": summary, "errors": errors}},
    #         status=status.HTTP_200_OK,
    #     )

    @action(detail=True, methods=["get"], url_path="error-report/download")
    def download_error_report(self, request, pk=None):
        """
            Download error report as CSV for a specific Gate Pass import log.

        #     Note: pk here is import_log_id, not gate_pass_id.
        #"""

    #     try:
    #         import_log = ImportLog.objects.get(id=pk, module_name="GatePass")
    #     except ImportLog.DoesNotExist:
    #         return Response(
    #             {"success": False, "message": "Import log not found"},
    #             status=status.HTTP_404_NOT_FOUND,
    #         )

    #     # report = ErrorReport(import_log)
    #     # csv_content = report.generate_csv_report()

    #     from django.http import HttpResponse

    #     # response = HttpResponse(csv_content, content_type="text/csv")
    #     response[
    #         "Content-Disposition"
    #     ] = f'attachment; filename="gate_pass_import_errors_{pk}.csv"'
    #     return response

    @action(detail=False, methods=["get"], url_path="load-po-items")
    def load_po_items_action(self, request):
        po_id = request.query_params.get("po_id")
        if not po_id:
            return Response(
                {
                    "success": False,
                    "message": "po_id query parameter is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            items = load_po_items(po_id)
            return Response(
                {"success": True, "data": items},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Failed to load PO items for %s: %s", po_id, exc)
            return custom_exception(exc)

    @action(detail=True, methods=["get"], url_path="print-data")
    def print_data(self, request, pk=None):
        instance = get_object_or_404(GatePass, pk=pk, deleted=False)
        serializer = GatePassPrintSerializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request):
        """Archive gate passes. Only CLOSED gate passes are archived (ERP rule)."""
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
            updated = bulk_archive_gate_passes(ids, request.user)
            msg = f"{updated} gate pass(es) archived successfully."
            if updated < len(ids):
                msg += " Only CLOSED gate passes can be archived."
            return Response(
                {"success": True, "message": msg},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Bulk archive gate passes failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        """Restore archived gate passes."""
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
            updated = bulk_restore_gate_passes(ids, request.user)
            qs = self.get_queryset().filter(id__in=ids)
            serializer = GatePassListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} gate pass(es) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Bulk restore gate passes failed: %s", exc)
            return custom_exception(exc)


class GatePassArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for archived gate passes. Consistent response format."""

    queryset = (
        GatePass.objects.filter(deleted=False, is_archived=True)
        .select_related("created_by", "updated_by")
        .annotate(items_count=Count("items"))
        .prefetch_related("items")
        .order_by("-updated_at")
    )
    serializer_class = GatePassListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "type",
        "status",
        "vehicle_no",
        "gate_pass_no",
        "po_id",
        "party_name",
    ]
    search_fields = [
        "gate_pass_no",
        "vehicle_no",
        "party_name",
        "remarks",
    ]
    ordering_fields = [
        "date",
        "created_at",
        "updated_at",
        "gate_pass_no",
        "status",
    ]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GatePassDetailSerializer
        return GatePassListSerializer

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
