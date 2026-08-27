from django_filters.rest_framework import DjangoFilterBackend
from vehicle_type.filters import VehicleTypeFilter
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from vehicle_type.permissions import VehicleTypePermission
from .models import VehicleType
from .serializer import VehicleTypeSerializer
from utils.export_excel import ExportUtility
from rest_framework.decorators import action
from rest_framework.response import Response

class VehicleTypeViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        VehicleType.objects.all()
        .select_related("created_by", "updated_by")
        .order_by("-id")
    )
    serializer_class = VehicleTypeSerializer
    filter_backends = BaseModelViewSet.filter_backends + [DjangoFilterBackend]
    filterset_class = VehicleTypeFilter
    permission_classes = BaseModelViewSet.permission_classes + [VehicleTypePermission]
    ordering_fields = BaseModelViewSet.ordering_fields + ["id", "vehicle_type"]


    @action(detail=False, methods=["GET"], url_path="export-pdf")
    def export_pdf(self, request):
        queryset = self.get_queryset().filter(deleted=False)

        fields = [
            "vehicle_type",
            "description",
            "created_at",
            "created_by__full_name",
            "updated_at",
            "updated_by__full_name",
        ]

        headers = [
            "Vehicle Type",
            "Description",
            "Created At",
            "Created By",
            "Updated At",
            "Updated By",
        ]

        return ExportUtility.export_to_pdf(
            queryset=queryset,
            fields=fields,
            headers=headers,
            file_name="vehicle_types.pdf",
            title="Vehicle Types Report",
        )
