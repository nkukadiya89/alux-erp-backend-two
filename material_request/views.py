from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from django.db.models import Count
from .models import MaterialRequest
from .serializers import MaterialRequestListSerializer, MaterialRequestSerializer, MaterialRequestDetailSerializer
from .permissions import MaterialRequestPermission
from material_request.models import MaterialRequestDetail
from material_request.permissions import RequestItemPermission


class MaterialRequestViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = MaterialRequest.objects.annotate(
        total_items=Count("material_request_detail")
    ).all().order_by("-id")
    serializer_class = MaterialRequestSerializer
    list_serializer_class = MaterialRequestListSerializer
    permission_classes = [MaterialRequestPermission]
    search_fields = (
        BaseModelViewSet.serching_fields + [
            "request_no",
            "department__name",
        ]
    )

    ordering_fields = (
        BaseModelViewSet.ordering_fields + [
            "id",
            "request_no",
            "date",
        ]
    )
    
class MaterialRequestDetailViewSet(BaseModelViewSet, ArchiveMixin):
        queryset = MaterialRequestDetail.objects.all().order_by("-id")
        serializer_class = MaterialRequestDetailSerializer
        permission_classes = [RequestItemPermission]
        search_fields = (BaseModelViewSet.serching_fields + [
            "sr_no",
            "item_code__material_name",
        ]
    )
        ordering_fields = BaseModelViewSet.ordering_fields + [
            "id",
            "sr_no",
        ]
    
