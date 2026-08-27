from rest_framework import serializers

from customer.sort_serializers import CustomerSortSerializer
from .models import PurchaseOrder, PurchaseOrderDetail
from utils.generate_number import generate_po_no


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderDetail
        fields = [
            "id",
            "item",
            "pending_qty",
            "ordered_qty",
            "rate",
            "tax",
            "store",
            "discount",
            "gst_type",
            "gst_amount",
            "transport_charge",
            "other_charge",
            "forwarding_charge",
            "hsn_code",
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    po_details = PurchaseOrderDetailSerializer(many=True)
    vendor_name = serializers.CharField(source="vendor.customer_name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_no",
            "payment_terms",
            "material_indent",
            "vendor",
            "vendor_name",
            "po_date",
            "delivery_date",
            "po_details",
            "request_no",
        ]

    def create(self, validated_data):
        po_details_data = validated_data.pop("po_details", [])
        validated_data["po_no"] = generate_po_no()

        purchase_order = PurchaseOrder.objects.create(
            **validated_data
        )

        for detail_data in po_details_data:
            PurchaseOrderDetail.objects.create(
                purchase_order=purchase_order,
                **detail_data
            )

        return purchase_order

    def update(self, instance, validated_data):
        details_data = validated_data.pop("po_details", None)
 
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
 
        instance.save()
 
        if details_data is not None:
            instance.po_details.all().delete()
 
            for detail in details_data:
                PurchaseOrderDetail.objects.create(
                    purchase_order=instance,
                    **detail
                )
 
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["vendor"] = (
            CustomerSortSerializer(instance.vendor).data
            if instance.vendor
            else None
        )
        
        return data