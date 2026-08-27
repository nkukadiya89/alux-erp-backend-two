from common.master_views import BaseModelViewSet
from .models import FurnaceMaster
from .serializers import FurnaceMasterSerializer
from .permissions import FurnaceMasterPermission
from common.models import ArchiveMixin

class FurnaceMasterViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = FurnaceMaster.objects.all().order_by("-id")
    serializer_class = FurnaceMasterSerializer
    permission_classes = [FurnaceMasterPermission]
    
    serching_fields = BaseModelViewSet.serching_fields + ["code", "name", "type"]


    ordering_fields = (
          BaseModelViewSet.ordering_fields + [
            "code",
            "name",
            "type",
        ]
     )