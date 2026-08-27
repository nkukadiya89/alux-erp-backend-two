from datetime import date
from rest_framework import serializers
from common.serializers import (
    BaseModelSerializer
)
from workorder.models import WorkOrder

from customer.sort_serializers import CustomerSortSerializer

class WorkOrdeSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["id", "order_no", "order_date"]


class WorkOrderListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    updated_by = serializers.CharField(source="updated_by.username", read_only=True)
    deleted_by = serializers.CharField(source="deleted_by.user_name", read_only=True)
    customer = CustomerSortSerializer(source="bill_to", read_only=True)
    salesorder = serializers.CharField(source="salesorder.sales_order_no", read_only=True, allow_null=True)
    total_weight = serializers.DecimalField(source="total_weight_calc", max_digits=10, decimal_places=3, read_only=True)
    total_dispatched_weight = serializers.DecimalField(
        source="total_dispatched_weight_calc",
        max_digits=10,
        decimal_places=3,
        read_only=True,
    )
    total_pending_weight = serializers.DecimalField(
        source="total_pending_weight_calc",
        max_digits=10,
        decimal_places=3,
        read_only=True,
    )
    total_packed_weight = serializers.DecimalField(
        source="total_packed_weight_calc",
        max_digits=10,
        decimal_places=3,
        read_only=True,
    )
    days_left = serializers.SerializerMethodField()
    class Meta(BaseModelSerializer.Meta):
        model = WorkOrder
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "order_no",
            "order_date",
            "delivery_date",
            "purchase_order_no",
            "purchase_order_date",
            "salesorder",
            "customer",
            "total_weight",
            "total_packed_weight",
            "total_dispatched_weight",
            "total_pending_weight",
            "days_left",
            "order_type",
            "status",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def get_days_left(self, obj):
        """Get the delivery date from related WorkOrderDetail instances."""
        delivery_date = obj.delivery_date
        if not delivery_date:
            return "-"
        delta = (delivery_date - date.today()).days
        if delta > 0:
            return f"{delta} days left"
        elif delta < 0:
            return f"{abs(delta)} days ago"
        else:
            return "Today"