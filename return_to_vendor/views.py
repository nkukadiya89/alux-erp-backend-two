from common.master_views import BaseModelViewSet
from .models import ReturnToVendor
from .serializers import ReturnToVendorSerializer
from .permissions import ReturnToVendorPermission


class ReturnToVendorViewSet(BaseModelViewSet):

    queryset = ReturnToVendor.objects.all().order_by("-id")
    serializer_class = ReturnToVendorSerializer
    permission_classes = [ReturnToVendorPermission]
    serching_fields = (
      BaseModelViewSet.serching_fields + [
        "grn",
        "item",
      ]
    )

    ordering_fields = (
          BaseModelViewSet.ordering_fields + [
            "id",
            "item",
            "customer",
            
         ]
     )