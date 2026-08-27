"""
Plant Type Capability Views
Handles CRUD operations for Plant Type ↔ Capability mapping
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.models import PlantCapability, PlantType, PlantTypeCapability
from common.serializers import (
    PlantTypeCapabilityListSerializer,
    PlantTypeCapabilitySerializer,
)
from common.services.plant_capability_service import (
    create_plant_type_capability_mapping,
    delete_plant_type_capability_mapping,
    validate_plant_type_capability_update,
)
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination

logger = logging.getLogger("file")


class PlantTypeCapabilityViewSet(ModelViewSet):
    """
    ViewSet for Plant Type Capability mapping
    """

    def _log_activity(self, user, action, mapping, request, payload):
        """Helper method to log user activity"""
        description = (
            f"{action} mapping: {mapping.plant_type.code} - {mapping.capability.code}"
        )
        if action == "CREATE":
            description = f"Assigned capability '{mapping.capability.code}' to plant type '{mapping.plant_type.code}'"
        elif action == "DELETE":
            description = f"Removed capability '{mapping.capability.code}' from plant type '{mapping.plant_type.code}'"

        log_user_activity(
            user=user,
            action=action,
            module_name="Plant Type Capability",
            description=description,
            request=request,
            payload=payload,
        )

    def _error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        """Helper method to create error response"""
        return Response(
            {"success": False, "message": message},
            status=status_code,
        )

    queryset = (
        PlantTypeCapability.objects.filter(is_deleted=False)
        .select_related("plant_type", "capability", "created_by", "updated_by")
        .order_by("plant_type__code", "capability__code")
    )
    serializer_class = PlantTypeCapabilitySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "plant_type__code",
        "plant_type__name",
        "capability__code",
        "capability__name",
    ]
    ordering_fields = [
        "plant_type__code",
        "capability__code",
        "status",
        "created_at",
    ]
    ordering = ["plant_type__code", "capability__code"]

    def get_queryset(self):
        queryset = super().get_queryset()
        plant_type_id = self.request.query_params.get("plant_type")
        capability_id = self.request.query_params.get("capability")
        status_filter = self.request.query_params.get("status")

        if plant_type_id:
            queryset = queryset.filter(plant_type_id=plant_type_id)
        if capability_id:
            queryset = queryset.filter(capability_id=capability_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def list(self, request, *args, **kwargs):
        """List all plant type capability mappings with pagination"""
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
        """Retrieve a single plant type capability mapping"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)

    def create(self, request, *args, **kwargs):
        """Assign a capability to a plant type"""
        try:
            payload = clean_payload(request.data)
            plant_type_id = request.data.get("plant_type")
            capability_id = request.data.get("capability")

            if not plant_type_id or not capability_id:
                return self._error_response("Plant type and capability are required.")

            mapping, error_message = create_plant_type_capability_mapping(
                plant_type_id=plant_type_id,
                capability_id=capability_id,
                user=request.user,
            )

            if not mapping:
                return self._error_response(error_message)

            self._log_activity(request.user, "CREATE", mapping, request, payload)

            serializer = self.get_serializer(mapping)
            return Response(
                {
                    "success": True,
                    "message": "Capability assigned to plant type successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return custom_exception(e)

    def update(self, request, *args, **kwargs):
        """Update a plant type capability mapping"""
        try:
            instance = self.get_object()
            payload = clean_payload(request.data)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            new_status = serializer.validated_data.get("status")
            can_update, error_message = validate_plant_type_capability_update(
                mapping=instance,
                new_status=new_status,
            )

            if not can_update:
                return self._error_response(error_message)

            instance.updated_by = request.user
            serializer.save()
            self._log_activity(request.user, "UPDATE", instance, request, payload)

            return Response(
                {
                    "success": True,
                    "message": "Plant Type Capability mapping updated successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Soft delete a plant type capability mapping"""
        try:
            instance = self.get_object()

            success, error_message = delete_plant_type_capability_mapping(
                mapping=instance,
                user=request.user,
            )

            if not success:
                return self._error_response(error_message)

            payload = clean_payload(request.data)
            self._log_activity(request.user, "DELETE", instance, request, payload)

            return Response(
                {
                    "success": True,
                    "message": "Capability mapping removed successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    @action(
        detail=False,
        methods=["get"],
        url_path="plant-type/(?P<plant_type_id>[^/.]+)/capabilities",
    )
    def list_by_plant_type(self, request, plant_type_id=None):
        """List all capabilities for a specific plant type"""
        try:
            try:
                plant_type = PlantType.objects.get(id=plant_type_id, is_deleted=False)
            except PlantType.DoesNotExist:
                return self._error_response(
                    "Plant type not found.", status.HTTP_404_NOT_FOUND
                )

            queryset = self.get_queryset().filter(plant_type=plant_type)
            queryset = self.filter_queryset(queryset)
            page = self.paginate_queryset(queryset)

            serializer = PlantTypeCapabilityListSerializer(
                page if page is not None else queryset, many=True
            )

            if page is not None:
                return self.get_paginated_response(
                    {
                        "success": True,
                        "data": serializer.data,
                    }
                )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)


class PlantTypeCapabilitiesListViewSet(ModelViewSet):
    """
    ViewSet to list capabilities for a specific plant type
    """

    queryset = PlantTypeCapability.objects.filter(is_deleted=False).select_related(
        "plant_type", "capability"
    )
    serializer_class = PlantTypeCapabilityListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["capability__code", "capability__name"]
    ordering_fields = ["capability__code", "status", "created_at"]
    ordering = ["capability__code"]

    def get_queryset(self):
        queryset = super().get_queryset()
        plant_type_id = self.kwargs.get("plant_type_id")

        if plant_type_id:
            queryset = queryset.filter(plant_type_id=plant_type_id, is_deleted=False)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def list(self, request, *args, **kwargs):
        """List capabilities for a plant type"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return custom_exception(e)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single plant type capability mapping"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return custom_exception(e)
