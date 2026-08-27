from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from return_qc.filters import ReturnQCFilter
from return_qc.models import ReturnQC, ReturnQCLine
from return_qc.serializers import ReturnQCLineSerializer, ReturnQCSerializer


class ReturnQCViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = (
        ReturnQC.objects.select_related(
            "vendor",
            "jobwork_invoice",
            "jobwork_type",
            "plant",
            "created_by",
            "updated_by",
            "shift",
        )
        .prefetch_related(
            Prefetch(
                "qc_lines",
                queryset=ReturnQCLine.objects.filter(deleted=False).select_related(
                    "production",
                    "workorder",
                    "workorder_detail",
                    "section_no",
                    "die_no",
                    "alloy",
                    "temper",
                ),
            )
        )
        .order_by("-created_at")
    )
    serializer_class = ReturnQCSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReturnQCFilter
    ordering_fields = ["id", "inspection_date", "inspection_no"]

    def get_instance_display(self, instance):
        return instance.inspection_no


class ReturnQCLineViewSet(ArchiveMixin, BaseModelViewSet):
    queryset = ReturnQCLine.objects.filter(deleted=False).order_by("-created_at")
    serializer_class = ReturnQCLineSerializer
