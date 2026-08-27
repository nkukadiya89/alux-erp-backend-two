from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
import logging

from common.master_views import BaseModelViewSet
from workorder.serializers import WorkOrderSerializers
from workorder.sort_serializers import WorkOrderListSerializer

from .models import WorkOrder

logger = logging.getLogger("file")


class OpenWorkOrderViewSet(BaseModelViewSet):
    serializer_class = WorkOrderSerializers
    list_serializer_class = WorkOrderListSerializer
    fy_filtering_enabled = True

    def get_queryset(self):
        queryset = WorkOrder.objects.filter(
            status__in=["Open", "Packed"], deleted=False
        )

        if self.action == "list":
            queryset = (
                queryset.select_related("bill_to", "created_by", "updated_by")
                .annotate(
                    total_weight_calc=Coalesce(
                        Sum(
                            "workorder_detail_workorder__net_weight",
                            filter=Q(workorder_detail_workorder__deleted=False),
                        ),
                        Value(0),
                        output_field=DecimalField(max_digits=20, decimal_places=3),
                    ),
                    total_packed_weight_calc=Coalesce(
                        Sum(
                            "workorder_detail_workorder__packed_weight",
                            filter=Q(workorder_detail_workorder__deleted=False),
                        ),
                        Value(0),
                        output_field=DecimalField(max_digits=20, decimal_places=3),
                    ),
                    total_dispatched_weight_calc=Coalesce(
                        Sum(
                            "workorder_detail_workorder__dispatched_weight",
                            filter=Q(workorder_detail_workorder__deleted=False),
                        ),
                        Value(0),
                        output_field=DecimalField(max_digits=20, decimal_places=3),
                    ),
                    total_pending_weight_calc=Coalesce(
                        Sum(
                            "workorder_detail_workorder__pending_weight",
                            filter=Q(workorder_detail_workorder__deleted=False),
                        ),
                        Value(0),
                        output_field=DecimalField(max_digits=20, decimal_places=3),
                    ),
                )
                .order_by("-id")
            )

        return queryset
