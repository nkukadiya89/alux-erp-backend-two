from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from dimension_inspection.filters import DimensionInspectionFilter
from dimension_inspection.models import DimensionInspection, DimensionInspectionDetail
from dimension_inspection.serializers import (
    DimensionInspectionDetailSerializer,
    DimensionInspectionSerializer,
)
from utils.custom_filters import SearchFilter
from django.db.models import Prefetch


class DimensionInspectionViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = (
        DimensionInspection.objects.select_related(
            "production",
            "workorder",
            "customer",
            "section",
            "alloy",
            "temper",
            "press",
            "created_by",
            "updated_by",
        )
        .prefetch_related(
            Prefetch(
                "dimension_inspection_details",
                queryset=DimensionInspectionDetail.objects.filter(deleted=False),
            )
        )
        .order_by("-created_at")
    )

    serializer_class = DimensionInspectionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DimensionInspectionFilter

    ordering_fields = ["id", "inspection_date", "created_at", "updated_at"]


class DimensionInspectionDetailViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = DimensionInspectionDetail.objects.all().order_by("-created_at")
    serializer_class = DimensionInspectionDetailSerializer
    filter_backends = [SearchFilter, OrderingFilter]
