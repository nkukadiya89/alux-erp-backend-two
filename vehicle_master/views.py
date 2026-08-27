import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin

from .filters import VehicleMasterFilter
from .models import VehicleMaster
from .permissions import VehicleMasterPermission
from .serializer import (
    VehicleMasterDropdownSerializer,
    VehicleMasterListSerializer,
    VehicleMasterSerializer,
)
from . import services

logger = logging.getLogger("file")


class VehicleMasterViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = VehicleMaster.objects.select_related(
        "party_name", "vehicle_type", "created_by", "updated_by", "deleted_by"
    ).all()
    serializer_class = VehicleMasterSerializer
    list_serializer_class = VehicleMasterListSerializer

    fy_filtering_enabled = False

    filter_backends = BaseModelViewSet.filter_backends + [DjangoFilterBackend]
    filterset_class = VehicleMasterFilter
    permission_classes = BaseModelViewSet.permission_classes + [VehicleMasterPermission]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "party_name",
        "vehicle_no",
        "tare_wt",
        "vehicle_type",
    ]
    search_fields = BaseModelViewSet.serching_fields + [
        "vehicle_no",
        "party_name__party_name",
        "vehicle_type__vehicle_type",
    ]

    def get_instance_display(self, instance):
        return str(instance.vehicle_no or instance.pk)

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = (
            VehicleMaster.objects.filter(deleted=False)
            .only("id", "vehicle_no")
            .order_by("vehicle_no")
        )
        serializer = VehicleMasterDropdownSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="vehicles_by_party")
    def get_vehicle_by_party(self, request):
        party_id = request.query_params.get("party_id")
        if not party_id:
            return Response(
                {"success": False, "message": "party_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            party_id = int(party_id)
        except ValueError:
            return Response(
                {"success": False, "message": "party_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = services.get_vehicles_by_party(party_id)
        page = self.paginate_queryset(queryset)
        data = [
            {"id": v.id, "vehicle_no": services.serialize_vehicle_no(v.vehicle_no)}
            for v in (page if page is not None else queryset)
        ]

        if page is not None:
            return self.get_paginated_response({"success": True, "data": data})

        return Response({"success": True, "count": len(data), "data": data})

    @action(detail=False, methods=["get"], url_path="vehicles_by_type")
    def get_vehicle_by_type(self, request):
        vehicle_type_id = request.query_params.get("vehicle_type_id")
        if not vehicle_type_id:
            return Response(
                {"success": False, "message": "vehicle_type_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            vehicle_type_id = int(vehicle_type_id)
        except ValueError:
            return Response(
                {"success": False, "message": "vehicle_type_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = services.get_vehicles_by_type(vehicle_type_id)
        data = [
            {"id": v.id, "vehicle_no": services.serialize_vehicle_no(v.vehicle_no)}
            for v in queryset
        ]
        return Response(
            {"success": True, "count": len(data), "data": data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="vehicle_type_by_vehicle")
    def get_vehicle_type_by_vehicle(self, request, pk=None):
        try:
            vehicle = services.get_vehicle_detail(pk)
        except VehicleMaster.DoesNotExist:
            return Response(
                {"success": False, "message": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "id": vehicle.id,
            "vehicle_no": vehicle.vehicle_no,
            "tare_wt": vehicle.tare_wt,
            "vehicle_type": {
                "id": vehicle.vehicle_type.id if vehicle.vehicle_type else None,
                "name": vehicle.vehicle_type.vehicle_type if vehicle.vehicle_type else None,
            },
            "party_name": {
                "id": vehicle.party_name.id if vehicle.party_name else None,
                "name": vehicle.party_name.party_name if vehicle.party_name else None,
            },
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
