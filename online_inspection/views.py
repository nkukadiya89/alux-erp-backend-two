from django_filters.rest_framework import DjangoFilterBackend
from common.models import ArchiveMixin
from common.master_views import BaseModelViewSet
from online_inspection.filters import OnlineInspectionFilter
from online_inspection.models import OnlineInspection
from online_inspection.permissions import OnlineInspectionPermission
from online_inspection.serializers import OnlineInspectionSerializer


class OnlineInspectionViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        OnlineInspection.objects.filter(deleted=False)
        .select_related("press", "shift", "created_by", "updated_by")
        .prefetch_related(
            "qc_rack_details__production",
            "qc_rack_details__section",
            "qc_rack_details__alloy",
            "qc_rack_details__temper",
        )
        .order_by("-id")
    )
    serializer_class = OnlineInspectionSerializer
    permission_classes = [OnlineInspectionPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OnlineInspectionFilter

    ordering_fields = ["inspection_date", "press__name"]
