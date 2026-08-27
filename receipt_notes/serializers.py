from rest_framework import serializers

from purchase_order.serializers import PurchaseOrderSerializer
from store.serializers import StoreSerializers
from .models import GoodsReceiptNote, GoodsReceiptNoteDetail
from utils.generate_number import generate_grn_request_no
from customer.sort_serializers import CustomerSortSerializer

class GoodsReceiptNoteDetailSerializer(serializers.ModelSerializer):
    grn = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = GoodsReceiptNoteDetail
        fields = "__all__"
        extra_kwargs = {
            "grn": {"read_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["store"] = StoreSerializers(instance.store).data if instance.store else None
        return data

class GoodsReceiptNoteSerializer(serializers.ModelSerializer):
    grn_details = GoodsReceiptNoteDetailSerializer(many=True, required=False)

    class Meta:
        model = GoodsReceiptNote
        fields = "__all__"
        extra_kwargs = {
            "grn_no": {"read_only": True},
        }

    def create(self, validated_data):
        details_data = validated_data.pop("grn_details", [])
        validated_data["grn_no"] = generate_grn_request_no()
        grn = GoodsReceiptNote.objects.create(**validated_data)

        for detail in details_data:
            GoodsReceiptNoteDetail.objects.create(grn=grn, **detail)

        return grn
    
    def update(self, instance, validated_data):
        details_data = validated_data.pop("grn_details", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
    
        if details_data is not None:
            instance.grn_details.all().delete()

            for detail in details_data:
                GoodsReceiptNoteDetail.objects.create(
                grn=instance,
                **detail
            )

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["vendor"] = CustomerSortSerializer(instance.vendor).data if instance.vendor else None
        data["purchase_order"] = PurchaseOrderSerializer(instance.purchase_order).data if instance.purchase_order else None
        return data


class GoodsReceiptNoteListSerializer(serializers.ModelSerializer):
    vendor = serializers.CharField(source="vendor.customer_name", read_only=True)
    po_no = serializers.CharField(source="purchase_order.po_no", read_only=True)
    received_by = serializers.CharField(source="received_by.first_name", read_only=True)
    class Meta:
        model = GoodsReceiptNote
        fields = "__all__"