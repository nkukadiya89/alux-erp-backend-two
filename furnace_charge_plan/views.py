from common.master_views import BaseModelViewSet
from .models import (FurnaceChargePlan, FurnaceChargePlanDetail)
from .serializers import (FurnaceChargePlanSerializer, FurnaceChargePlanDetailSerializer)
from .permissions import (FurnaceChargePlanPermission, FurnaceChargePlanDetailPermission)


class FurnaceChargePlanViewSet(BaseModelViewSet):

    queryset = FurnaceChargePlan.objects.all()
    serializer_class = FurnaceChargePlanSerializer
    permission_classes = [FurnaceChargePlanPermission]

    serching_fields = (
        BaseModelViewSet.serching_fields + [
            "plan_no",
            "furnace__name",
            "alloy_type__name",
            "supervisor__username",
        ]
    )

    ordering_fields = (
        BaseModelViewSet.ordering_fields + [
            "id",
            "plan_no",
            "date",
        ]
    )


class FurnaceChargePlanDetailViewSet(BaseModelViewSet):

    queryset = FurnaceChargePlanDetail.objects.all().order_by("-id")
    serializer_class = FurnaceChargePlanDetailSerializer
    permission_classes = BaseModelViewSet.permission_classes + [FurnaceChargePlanDetailPermission]

    serching_fields = (
        BaseModelViewSet.serching_fields + [
            "material__name",
            "store__name",
        ]
    )

    ordering_fields = (
        BaseModelViewSet.ordering_fields + [
            "id",
            "planned_qty",
        ]
    )