"""
Scrap Generation Remelt REST API.
CRUD, submit, complete, cancel-submit, bulk archive/restore, archived list, dropdowns.
"""

import logging

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Store
from utils.error_handling import custom_exception
from utils.pagination import Pagination

from .models import ScrapGenerationRemelt
from .serializers import (
    ScrapGenerationRemeltCompleteSerializer,
    ScrapGenerationRemeltDetailSerializer,
    ScrapGenerationRemeltListSerializer,
    ScrapGenerationRemeltSubmitSerializer,
    ScrapGenerationRemeltWriteSerializer,
)
from .services import (
    archive_scrap_generation_remelts,
    cancel_submit,
    complete_scrap_generation_remelt,
    restore_scrap_generation_remelts,
    submit_scrap_generation_remelt,
)

logger = logging.getLogger("file")


class RemeltStoreDropdownView(APIView):
    """GET /api/v1/stores/remelt-store-dropdown/?plant_id=&kind=source|destination"""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        plant_id = request.query_params.get("plant_id")
        kind = (request.query_params.get("kind") or "").lower().strip()

        qs = (
            Store.objects.filter(deleted=False)
            .select_related("store_type", "plant")
            .order_by("store_code")
        )
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        if kind == "source":
            qs = qs.filter(
                Q(store_type__name__icontains="wip")
                | Q(store_type__name__icontains="melting")
            )
        if kind == "destination":
            qs = qs.filter(store_type__name__icontains="scrap")

        data = [
            {
                "id": str(s.id),
                "store_code": s.store_code,
                "store_name": s.store_name,
                "plant_id": str(s.plant_id),
                "plant_code": getattr(s.plant, "plant_code", None),
                "store_type_name": getattr(s.store_type, "name", None),
            }
            for s in qs
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class RemeltItemsAvailableInStoreView(APIView):
    """GET /api/v1/scrap-generation-remelts/items/available-in-store/?plant_id=&store_id="""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        plant_id = request.query_params.get("plant_id")
        store_id = request.query_params.get("store_id")
        if not plant_id or not store_id:
            return Response(
                {
                    "success": False,
                    "message": "plant_id and store_id query parameters are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

class ScrapGenerationRemeltViewSet(viewsets.ModelViewSet):
    queryset = ScrapGenerationRemelt.objects.none()
    serializer_class = ScrapGenerationRemeltWriteSerializer
    list_serializer_class = ScrapGenerationRemeltListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "status",
        "remelt_date",
        "plant",
        "source_store",
        "destination_store",
        "remelt_no",
    ]
    search_fields = [
        "remelt_no",
        "remarks",
        "plant__plant_code",
        "plant__plant_name",
        "source_store__store_code",
        "source_store__store_name",
        "destination_store__store_code",
        "destination_store__store_name",
    ]
    ordering_fields = [
        "remelt_date",
        "created_at",
        "updated_at",
        "remelt_no",
        "total_qty",
    ]
    ordering = ["-remelt_date", "-created_at"]

    def get_queryset(self):
        return (
            ScrapGenerationRemelt.objects.filter(is_archived=False)
            .select_related(
                "plant",
                "source_store",
                "destination_store",
                "created_by",
                "updated_by",
            )
            .prefetch_related("items__item", "items__uom")
            .order_by("-remelt_date", "-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        if self.action in ("create", "update", "partial_update"):
            return ScrapGenerationRemeltWriteSerializer
        return ScrapGenerationRemeltDetailSerializer

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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = ScrapGenerationRemeltDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt create failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.status != ScrapGenerationRemelt.STATUS_DRAFT:
            return Response(
                {"success": False, "message": "Only DRAFT records can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            out_serializer = ScrapGenerationRemeltDetailSerializer(instance)
            return Response(
                {"success": True, "data": out_serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt update failed: %s", exc)
            return custom_exception(exc)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != ScrapGenerationRemelt.STATUS_DRAFT:
            return Response(
                {"success": False, "message": "Only DRAFT records can be archived."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_archived = True
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(
            {
                "success": True,
                "message": "Scrap generation remelt archived successfully.",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        remelt = get_object_or_404(ScrapGenerationRemelt, pk=pk, is_archived=False)
        ser = ScrapGenerationRemeltSubmitSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = submit_scrap_generation_remelt(remelt, request.user)
            data = ScrapGenerationRemeltDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Record submitted successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt submit failed: %s", exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        remelt = get_object_or_404(ScrapGenerationRemelt, pk=pk, is_archived=False)
        ser = ScrapGenerationRemeltCompleteSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            updated = complete_scrap_generation_remelt(remelt, request.user)
            data = ScrapGenerationRemeltDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Record completed successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt complete failed: %s", exc)
            return custom_exception(exc)

    @action(detail=True, methods=["post"], url_path="cancel-submit")
    def cancel_submit(self, request, pk=None):
        remelt = get_object_or_404(ScrapGenerationRemelt, pk=pk, is_archived=False)
        try:
            updated = cancel_submit(remelt, request.user)
            data = ScrapGenerationRemeltDetailSerializer(updated).data
            return Response(
                {
                    "success": True,
                    "data": data,
                    "message": "Submit cancelled; status reverted to DRAFT.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt cancel-submit failed: %s", exc)
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
            updated = archive_scrap_generation_remelts(ids, request.user)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} record(s) archived successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt bulk archive failed: %s", exc)
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
            updated = restore_scrap_generation_remelts(ids, request.user)
            qs = (
                ScrapGenerationRemelt.objects.filter(id__in=ids)
                .select_related(
                    "plant",
                    "source_store",
                    "destination_store",
                    "created_by",
                    "updated_by",
                )
                .prefetch_related("items__item", "items__uom")
            )
            serializer = ScrapGenerationRemeltListSerializer(qs, many=True)
            return Response(
                {
                    "success": True,
                    "message": f"{updated} record(s) restored successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Scrap generation remelt bulk restore failed: %s", exc)
            return custom_exception(exc)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = self.get_queryset().filter(
            status__in=[
                ScrapGenerationRemelt.STATUS_DRAFT,
                ScrapGenerationRemelt.STATUS_SUBMITTED,
            ]
        )
        serializer = ScrapGenerationRemeltListSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )


class ScrapGenerationRemeltArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        ScrapGenerationRemelt.objects.filter(is_archived=True)
        .select_related(
            "plant", "source_store", "destination_store", "created_by", "updated_by"
        )
        .prefetch_related("items__item", "items__uom")
        .order_by("-updated_at")
    )
    serializer_class = ScrapGenerationRemeltListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "plant", "remelt_no"]
    search_fields = ["remelt_no", "remarks"]
    ordering_fields = ["remelt_date", "updated_at", "remelt_no"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ScrapGenerationRemeltDetailSerializer
        return ScrapGenerationRemeltListSerializer

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
