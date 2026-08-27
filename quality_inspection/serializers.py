from rest_framework import serializers
from customer.sort_serializers import CustomerSortSerializer
from purchase_order.serializers import PurchaseOrderSerializer
from receipt_notes.serializers import GoodsReceiptNoteSerializer
from utils.generate_number import generate_quality_inspection_no
from .models import QualityInspection


class QualityInspectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = QualityInspection
        fields = "__all__"
        extra_kwargs = {
            "inspection_no": {"read_only": True},
        }

    def create(self, validated_data):
        validated_data["inspection_no"] = generate_quality_inspection_no()
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["purchase_order"] = PurchaseOrderSerializer(instance.purchase_order).data if instance.purchase_order else None
        data["grn"] = GoodsReceiptNoteSerializer(instance.grn).data if instance.grn else None
        data["vendor"] = CustomerSortSerializer(instance.vendor).data if instance.vendor else None
        return data