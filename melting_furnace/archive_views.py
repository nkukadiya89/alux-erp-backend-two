from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.custom_filters import CustomSearchFilter
from utils.pagination import Pagination

from .models import AdditiveMaster, Furnace, RecoveryStandard
from .serializers import (
    AdditiveMasterSerializer,
    FurnaceSerializer,
    RecoveryStandardSerializer,
)


class FurnaceArchiveViewSet(ModelViewSet):
    """
    ViewSet for Archived Furnaces (soft deleted)
    Read-only access to archived furnaces
    """

    queryset = (
        Furnace.objects.filter(deleted=True)
        .select_related("created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = FurnaceSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = ["status", "furnace_type"]
    search_fields = [
        "furnace_code",
        "furnace_name",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = ["furnace_name", "furnace_code", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]  # Read-only - only GET for list/retrieve

    def get_queryset(self):
        """Filter archived furnaces"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived furnaces"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response({"success": True, "data": paginated_response.data})

        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single archived furnace"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})


class AdditiveMasterArchiveViewSet(ModelViewSet):
    """
    ViewSet for Archived Additive Masters (soft deleted)
    Read-only access to archived additive masters
    """

    queryset = (
        AdditiveMaster.objects.filter(deleted=True)
        .select_related("created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = AdditiveMasterSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = ["status", "category", "unit"]
    search_fields = [
        "additive_code",
        "additive_name",
        "category__name",
        "unit__name",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = ["additive_name", "additive_code", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]

    def get_queryset(self):
        """Filter archived additive masters"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived additive masters"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response({"success": True, "data": paginated_response.data})

        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single archived additive master"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})


class RecoveryStandardArchiveViewSet(ModelViewSet):
    """
    ViewSet for Archived Recovery Standards (soft deleted)
    Read-only access to archived recovery standards
    """

    queryset = (
        RecoveryStandard.objects.filter(deleted=True)
        .select_related("created_by", "updated_by")
        .order_by("-updated_at")
    )
    serializer_class = RecoveryStandardSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, CustomSearchFilter, OrderingFilter]

    filterset_fields = ["status", "furnace_type", "material_type"]
    search_fields = [
        "furnace_type__name",
        "material_type",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = ["material_type", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    http_method_names = ["get"]

    def get_queryset(self):
        """Filter archived recovery standards"""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        """List all archived recovery standards"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response({"success": True, "data": paginated_response.data})

        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single archived recovery standard"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})
