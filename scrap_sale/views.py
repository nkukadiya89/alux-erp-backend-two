"""
Scrap Sale REST API.
CRUD, finalize, cancel, bulk-archive/restore, dropdown, available-for-sale.
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

from .models import ScrapSale
from .serializers import (
    ScrapSaleCancelSerializer,
    ScrapSaleDetailSerializer,
    ScrapSaleDropdownSerializer,
    ScrapSaleFinalizeSerializer,
    ScrapSaleListSerializer,
    ScrapSaleWriteSerializer,
)
from .services import (
    archive_scrap_sales,
    cancel_scrap_sale,
    finalize_scrap_sale,
    get_available_scrap_items_for_sale,
    restore_scrap_sales,
)

logger = logging.getLogger("file")


class ScrapSaleViewSet(viewsets.ModelViewSet):
    """
    CRUD and status actions for Scrap Sale.
    List/create/retrieve/update/partial_update/destroy,
    finalize, cancel, bulk-archive, bulk-restore, dropdown.
    """

    queryset = ScrapSale.objects.none()  # overridden in get_queryset
    serializer_class = ScrapSaleWriteSerializer
    list_serializer_class = ScrapSaleListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "customer", "sale_no"]
    search_fields = ["sale_no", "dispatch_ref", "remarks", "customer__customer_name"]
    ordering_fields = [
        "sale_date",
        "created_at",
        "updated_at",
        "sale_no",
        "total_value",
    ]
    ordering = ["-sale_date", "-created_at"]

    def get_queryset(self):
        return (
            ScrapSale.objects.filter(is_archived=False)
            .select_related("customer", "created_by", "updated_by")
            .prefetch_related("items__scrap_item", "items__uom")
            .order_by("-sale_date", "-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        if self.action in ("create", "update", "partial_update"):
            return ScrapSaleWriteSerializer
        return ScrapSaleDetailSerializer

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
            out_serializer = ScrapSaleDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.exception("Scrap sale create failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.status != ScrapSale.STATUS_DRAFT:
            return Response(
                {"success": False, "message": "Only DRAFT scrap sales can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = ScrapSaleDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap sale update failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == ScrapSale.STATUS_FINALIZED:
            return Response(
                {
                    "success": False,
                    "message": "FINALIZED scrap sales cannot be archived. Use reversal module for finalized records.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_archived = True
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(
            {"success": True, "message": "Scrap sale archived successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        scrap_sale = get_object_or_404(ScrapSale, pk=pk, is_archived=False)
        ser = ScrapSaleFinalizeSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = finalize_scrap_sale(scrap_sale, request.user)
            data = ScrapSaleDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Scrap sale finalized successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap sale finalize failed: %s", exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        scrap_sale = get_object_or_404(ScrapSale, pk=pk, is_archived=False)
        ser = ScrapSaleCancelSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = cancel_scrap_sale(scrap_sale, request.user)
            data = ScrapSaleDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Scrap sale cancelled successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap sale cancel failed: %s", exc)
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
            updated = archive_scrap_sales(ids, request.user)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap sale(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap sale bulk_archive failed: %s", exc)
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
            updated = restore_scrap_sales(ids, request.user)
            qs = (
                ScrapSale.objects.filter(id__in=ids)
                .select_related("customer", "created_by", "updated_by")
                .prefetch_related("items__scrap_item", "items__uom")
            )
            serializer = ScrapSaleListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} scrap sale(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap sale bulk_restore failed: %s", exc)
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = self.get_queryset().filter(
            status__in=[ScrapSale.STATUS_DRAFT, ScrapSale.STATUS_FINALIZED]
        )
        serializer = ScrapSaleDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class ScrapSaleArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list/retrieve for archived scrap sales."""

    queryset = (
        ScrapSale.objects.filter(is_archived=True)
        .select_related("customer", "created_by", "updated_by")
        .prefetch_related("items__scrap_item", "items__uom")
        .order_by("-updated_at")
    )
    serializer_class = ScrapSaleListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "customer", "sale_no"]
    search_fields = ["sale_no", "dispatch_ref", "remarks", "customer__customer_name"]
    ordering_fields = ["sale_date", "updated_at", "sale_no"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ScrapSaleDetailSerializer
        return ScrapSaleListSerializer

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


class ScrapItemViewSet(viewsets.ViewSet):
    """Scrap items: GET available-for-sale (list with available qty)."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=["get"], url_path="available-for-sale")
    def available_for_sale(self, request):
        try:
            data = get_available_scrap_items_for_sale()
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap items available-for-sale failed: %s", exc)
            return custom_exception(exc)
