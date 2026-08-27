"""
Scrap Transfer REST API.
CRUD, submit, complete, cancel-submit, bulk-archive/restore, archived list, dropdowns.
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
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.error_handling import custom_exception
from utils.pagination import Pagination

from .models import ScrapTransfer
from .serializers import (
    ScrapTransferDetailSerializer,
    ScrapTransferListSerializer,
    ScrapTransferWriteSerializer,
    ScrapTransferSubmitSerializer,
    ScrapTransferCompleteSerializer,
)
from .services import (
    archive_scrap_transfers,
    cancel_submit,
    complete_scrap_transfer,
    restore_scrap_transfers,
    submit_scrap_transfer,
)
from .services.scrap_transfer_service import get_available_scrap_items_in_store
from store.models import Store

logger = logging.getLogger("file")


class ScrapStoreDropdownView(APIView):
    """GET /api/v1/stores/scrap-store-dropdown/ - list stores that are scrap type."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        stores = (
            Store.objects.filter(deleted=False, store_type__name__icontains="scrap")
            .select_related("store_type", "plant")
            .order_by("store_code")
        )
        data = [
            {
                "id": str(s.id),
                "store_code": s.store_code,
                "store_name": s.store_name,
                "plant_id": str(s.plant_id),
                "plant_code": getattr(s.plant, "plant_code", None),
            }
            for s in stores
        ]
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK,
        )


class ScrapTransferViewSet(viewsets.ModelViewSet):
    """
    CRUD and status actions for Scrap Transfer.
    List/create/retrieve/update/partial_update/destroy (soft delete only DRAFT),
    submit, complete, cancel-submit, bulk-archive, bulk-restore.
    """

    queryset = ScrapTransfer.objects.none()
    serializer_class = ScrapTransferWriteSerializer
    list_serializer_class = ScrapTransferListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "status",
        "transfer_date",
        "from_store",
        "to_plant",
        "to_store",
        "transfer_no",
    ]
    search_fields = [
        "transfer_no",
        "remarks",
        "from_store__store_code",
        "from_store__store_name",
        "to_plant__plant_code",
        "to_plant__plant_name",
        "to_store__store_code",
    ]
    ordering_fields = [
        "transfer_date",
        "created_at",
        "updated_at",
        "transfer_no",
        "total_qty",
    ]
    ordering = ["-transfer_date", "-created_at"]

    def get_queryset(self):
        return (
            ScrapTransfer.objects.filter(is_archived=False)
            .select_related(
                "from_store", "to_plant", "to_store", "created_by", "updated_by"
            )
            .prefetch_related("items__scrap_item", "items__uom")
            .order_by("-transfer_date", "-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        if self.action in ("create", "update", "partial_update"):
            return ScrapTransferWriteSerializer
        return ScrapTransferDetailSerializer

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
            out_serializer = ScrapTransferDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.exception("Scrap transfer create failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.status != ScrapTransfer.STATUS_DRAFT:
            return Response(
                {
                    "success": False,
                    "message": "Only DRAFT scrap transfers can be edited.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = ScrapTransferDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap transfer update failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != ScrapTransfer.STATUS_DRAFT:
            return Response(
                {
                    "success": False,
                    "message": "Only DRAFT scrap transfers can be archived.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_archived = True
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(
            {"success": True, "message": "Scrap transfer archived successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        transfer = get_object_or_404(ScrapTransfer, pk=pk, is_archived=False)
        ser = ScrapTransferSubmitSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = submit_scrap_transfer(transfer, request.user)
            data = ScrapTransferDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Scrap transfer submitted successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap transfer submit failed: %s", exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        transfer = get_object_or_404(ScrapTransfer, pk=pk, is_archived=False)
        ser = ScrapTransferCompleteSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = complete_scrap_transfer(transfer, request.user)
            data = ScrapTransferDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Scrap transfer completed successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap transfer complete failed: %s", exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="cancel-submit")
    def cancel_submit(self, request, pk=None):
        transfer = get_object_or_404(ScrapTransfer, pk=pk, is_archived=False)
        try:
            updated = cancel_submit(transfer, request.user)
            data = ScrapTransferDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Submit cancelled; status reverted to DRAFT.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap transfer cancel-submit failed: %s", exc)
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
            updated = archive_scrap_transfers(ids, request.user)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap transfer(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap transfer bulk_archive failed: %s", exc)
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
            updated = restore_scrap_transfers(ids, request.user)
            qs = (
                ScrapTransfer.objects.filter(id__in=ids)
                .select_related(
                    "from_store", "to_plant", "to_store", "created_by", "updated_by"
                )
                .prefetch_related("items__scrap_item", "items__uom")
            )
            serializer = ScrapTransferListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap transfer(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap transfer bulk_restore failed: %s", exc)
            return custom_exception(exc)


class ScrapTransferArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list/retrieve for archived scrap transfers."""

    queryset = (
        ScrapTransfer.objects.filter(is_archived=True)
        .select_related(
            "from_store", "to_plant", "to_store", "created_by", "updated_by"
        )
        .prefetch_related("items__scrap_item", "items__uom")
        .order_by("-updated_at")
    )
    serializer_class = ScrapTransferListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "to_plant", "transfer_no"]
    search_fields = ["transfer_no", "remarks"]
    ordering_fields = ["transfer_date", "updated_at", "transfer_no"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ScrapTransferDetailSerializer
        return ScrapTransferListSerializer

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


class ScrapItemsAvailableInStoreView(APIView):
    """GET /api/v1/scrap-transfers/scrap-items/available-in-store/?store_id=<uuid>"""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        store_id = request.query_params.get("store_id")
        if not store_id:
            return Response(
                {"success": False, "message": "store_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = get_available_scrap_items_in_store(store_id)
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap items available-in-store failed: %s", exc)
            return custom_exception(exc)
