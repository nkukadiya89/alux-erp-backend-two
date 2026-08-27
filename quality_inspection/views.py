from common.master_views import BaseModelViewSet
from .models import QualityInspection
from .serializers import QualityInspectionSerializer
from .permissions import QualityInspectionPermission
from common.models import ArchiveMixin

class QualityInspectionViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = QualityInspection.objects.select_related("purchase_order", "grn", "vendor", "inspected_by").all()
    serializer_class = QualityInspectionSerializer
    permission_classes = BaseModelViewSet.permission_classes + [QualityInspectionPermission]
    search_fields = (
        BaseModelViewSet.serching_fields + [
            "inspected_by",
            "type",
            "status",
            "purchase_order__po_no",
            "grn__grn_no",
            "vendor__customer_name",
        ]
    )
    
    ordering_fields = (
        BaseModelViewSet.ordering_fields + [
            "inspected_by",
            "type",
            "date",
            "purchase_order",
            "grn",
            "vendor",
        ]
    )