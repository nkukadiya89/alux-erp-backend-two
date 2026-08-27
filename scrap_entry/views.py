"""
Scrap Entry REST API.
CRUD, post, mark-transferred, bulk-archive/restore, archived list, dropdowns.
"""

import logging

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.error_handling import custom_exception
from utils.pagination import Pagination

from .models import ScrapEntry, ScrapType, Process
from .serializers import (
    ScrapEntryDetailSerializer,
    ScrapEntryListSerializer,
    ScrapEntryPostSerializer,
    ScrapEntryTransferSerializer,
    ScrapEntryWriteSerializer,
    ScrapEntryDropdownSerializer,
    ScrapTypeListSerializer,
    ScrapTypeDetailSerializer,
    ScrapTypeWriteSerializer,
    ScrapTypeDropdownSerializer,
    ProcessListSerializer,
    ProcessDetailSerializer,
    ProcessWriteSerializer,
    ProcessDropdownSerializer,
)
from .services import (
    archive_scrap_entries,
    archive_scrap_types,
    archive_processes,
    post_scrap_entry,
    restore_scrap_entries,
    restore_scrap_types,
    restore_processes,
    mark_scrap_transferred,
)

logger = logging.getLogger("file")


class ScrapEntryViewSet(viewsets.ModelViewSet):
    """
    CRUD and status actions for Scrap Entry.
    List/create/retrieve/update/partial_update/destroy (archive only DRAFT),
    post, mark-transferred, bulk-archive, bulk-restore, dropdown.
    """

    queryset = ScrapEntry.objects.none()
    serializer_class = ScrapEntryWriteSerializer
    list_serializer_class = ScrapEntryListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "plant", "source_department", "entry_no"]
    search_fields = [
        "entry_no",
        "source_ref",
        "remarks",
        "plant__plant_code",
        "plant__plant_name",
    ]
    ordering_fields = ["date", "created_at", "updated_at", "entry_no", "total_qty"]
    ordering = ["-date", "-created_at"]

    def get_queryset(self):
        return (
            ScrapEntry.objects.filter(is_archived=False)
            .select_related("plant", "source_department", "created_by", "updated_by")
            .prefetch_related(
                "items__item",
                "items__scrap_type",
                "items__process",
                "items__uom",
                "items__store",
            )
            .order_by("-date", "-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        if self.action in ("create", "update", "partial_update"):
            return ScrapEntryWriteSerializer
        return ScrapEntryDetailSerializer

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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = ScrapEntryDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.exception("Scrap entry create failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.status != ScrapEntry.STATUS_DRAFT:
            return Response(
                {
                    "success": False,
                    "message": "Only DRAFT scrap entries can be edited.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = ScrapEntryDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap entry update failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != ScrapEntry.STATUS_DRAFT:
            return Response(
                {
                    "success": False,
                    "message": "Only DRAFT scrap entries can be archived.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_archived = True
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(
            {"success": True, "message": "Scrap entry archived successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="post")
    def post(self, request, pk=None):
        scrap_entry = get_object_or_404(ScrapEntry, pk=pk, is_archived=False)
        ser = ScrapEntryPostSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = post_scrap_entry(scrap_entry, request.user)
            data = ScrapEntryDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Scrap entry posted successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap entry post failed: %s", exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="mark-transferred")
    def mark_transferred(self, request, pk=None):
        scrap_entry = get_object_or_404(ScrapEntry, pk=pk, is_archived=False)
        ser = ScrapEntryTransferSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = mark_scrap_transferred(scrap_entry, request.user)
            data = ScrapEntryDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Scrap entry marked as transferred.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap entry mark-transferred failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = archive_scrap_entries(ids, request.user)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap entry(ies) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap entry bulk_archive failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {
                    "success": False,
                    "message": "ids list is required in the request body.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = restore_scrap_entries(ids, request.user)
            qs = (
                ScrapEntry.objects.filter(id__in=ids)
                .select_related(
                    "plant", "source_department", "created_by", "updated_by"
                )
                .prefetch_related(
                    "items__item",
                    "items__scrap_type",
                    "items__process",
                    "items__uom",
                    "items__store",
                )
            )
            serializer = ScrapEntryListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap entry(ies) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap entry bulk_restore failed: %s", exc)
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = self.get_queryset().filter(
            status__in=[ScrapEntry.STATUS_DRAFT, ScrapEntry.STATUS_POSTED]
        )
        serializer = ScrapEntryDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class ScrapEntryArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list/retrieve for archived scrap entries."""

    queryset = (
        ScrapEntry.objects.filter(is_archived=True)
        .select_related("plant", "source_department", "created_by", "updated_by")
        .prefetch_related(
            "items__item",
            "items__scrap_type",
            "items__process",
            "items__uom",
            "items__store",
        )
        .order_by("-updated_at")
    )
    serializer_class = ScrapEntryListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "plant", "entry_no"]
    search_fields = ["entry_no", "source_ref", "remarks"]
    ordering_fields = ["date", "updated_at", "entry_no"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ScrapEntryDetailSerializer
        return ScrapEntryListSerializer

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


# ----- ScrapType: full CRUD + archive/restore + dropdown -----
class ScrapTypeViewSet(viewsets.ModelViewSet):
    """CRUD, bulk-archive, bulk-restore, dropdown for ScrapType."""

    queryset = (
        ScrapType.objects.filter(is_archived=False)
        .select_related("category", "created_by", "updated_by")
        .order_by("code")
    )
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["code", "is_archived"]
    search_fields = ["code", "name", "category__category_code"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]
    ordering = ["code"]

    def get_serializer_class(self):
        if self.action == "list":
            return ScrapTypeListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ScrapTypeWriteSerializer
        if self.action == "retrieve":
            return ScrapTypeDetailSerializer
        return ScrapTypeDropdownSerializer

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
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_archived = True
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(
            {"success": True, "message": "Scrap type archived successfully."},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = archive_scrap_types(ids, request.user)
            return Response(
                {"success": True, "message": f"{updated} scrap type(s) archived."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap type bulk_archive failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = restore_scrap_types(ids, request.user)
            qs = ScrapType.objects.filter(id__in=ids).select_related(
                "category", "created_by", "updated_by"
            )
            serializer = ScrapTypeListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap type(s) restored.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap type bulk_restore failed: %s", exc)
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = ScrapType.objects.filter(is_archived=False).order_by("code")
        serializer = ScrapTypeDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )


class ScrapTypeArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """List/retrieve archived ScrapTypes."""

    queryset = (
        ScrapType.objects.filter(is_archived=True)
        .select_related("category", "created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = ScrapTypeListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["code", "name"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        return (
            ScrapTypeDetailSerializer
            if self.action == "retrieve"
            else ScrapTypeListSerializer
        )

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
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ScrapTypeDetailSerializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )


# ----- Process: full CRUD + archive/restore + dropdown -----
class ProcessViewSet(viewsets.ModelViewSet):
    """CRUD, bulk-archive, bulk-restore, dropdown for Process."""

    queryset = (
        Process.objects.filter(is_archived=False)
        .select_related("created_by", "updated_by")
        .order_by("code")
    )
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["code", "is_archived"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]
    ordering = ["code"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcessListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProcessWriteSerializer
        if self.action == "retrieve":
            return ProcessDetailSerializer
        return ProcessDropdownSerializer

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
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_archived = True
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(
            {"success": True, "message": "Process archived successfully."},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = archive_processes(ids, request.user)
            return Response(
                {"success": True, "message": f"{updated} process(es) archived."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Process bulk_archive failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = restore_processes(ids, request.user)
            qs = Process.objects.filter(id__in=ids).select_related(
                "created_by", "updated_by"
            )
            serializer = ProcessListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} process(es) restored.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Process bulk_restore failed: %s", exc)
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = Process.objects.filter(is_archived=False).order_by("code")
        serializer = ProcessDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )


class ProcessArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """List/retrieve archived Processes."""

    queryset = (
        Process.objects.filter(is_archived=True)
        .select_related("created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = ProcessListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["code", "name"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        return (
            ProcessDetailSerializer
            if self.action == "retrieve"
            else ProcessListSerializer
        )

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
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ProcessDetailSerializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )
