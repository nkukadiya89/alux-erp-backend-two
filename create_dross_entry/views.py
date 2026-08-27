from common.master_views import BaseModelViewSet
from .models import DrossEntry, DrossDetail
from .serializers import DrossEntrySerializer, DrossDetailSerializer
from .permissions import DrossEntryPermission, DrossDetailPermission


class DrossEntryViewSet(BaseModelViewSet):
    queryset = DrossEntry.objects.all()
    serializer_class = DrossEntrySerializer
    permission_classes = [DrossEntryPermission]

    serching_fields = (
        BaseModelViewSet.serching_fields + [
            "dross_entry_no",
        ]
    )

    ordering_fields = (
        BaseModelViewSet.ordering_fields + [
            "dross_entry_no",
            "shift",
        ]
    )

class DrossDetailViewSet(BaseModelViewSet):
    queryset = DrossDetail.objects.all()
    serializer_class = DrossDetailSerializer
    permission_classes = [DrossDetailPermission]

    serching_fields = (
        BaseModelViewSet.serching_fields + [
            "dross_type",
        ]
    )

    ordering_fields = (
        BaseModelViewSet.ordering_fields + [
            "dross_type",
        ]
    )