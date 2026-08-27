from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import serializers
from common.serializers import BaseModelSerializer
from vehicle_master.models import VehicleMaster

from .models import ManualWeightEntry

User = get_user_model()


class ManualWeightEntrySerializer(BaseModelSerializer):
    party_name_display = serializers.CharField(
        source="party_name.party_name", read_only=True
    )
    vehicle_type_name = serializers.CharField(
        source="vehicle_type.vehicle_type", read_only=True
    )
    material_name = serializers.CharField(source="material.item_name", read_only=True)

    vehicle_no = serializers.PrimaryKeyRelatedField(
        queryset=VehicleMaster.objects.filter(deleted=False),
        required=False,
        allow_null=True,
    )
    vehicle_no_display = serializers.CharField(
        source="vehicle_no.vehicle_no",
        read_only=True,
    )
    purchaser_name = serializers.CharField(
        source="purchaser.get_full_name", read_only=True
    )
    seller_name = serializers.CharField(source="seller.get_full_name", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = ManualWeightEntry
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "cash_party_name",
            "gross_weight",
            "tare_weight",
            "net_weight",
            "date_time_first",
            "date_time_second",
            "mound",
            "serial_no",
            "total_copy",
            "vehicle_no",
            "vehicle_no_display",
            "vehicle_type",
            "vehicle_type_name",
            "party_name",
            "party_name_display",
            "purchaser",
            "purchaser_name",
            "party_mobile_no",
            "material",
            "material_name",
            "capture_photo_manual_1",
            "capture_photo_manual_2",
            "seller",
            "seller_name",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        instance = ManualWeightEntry(**validated_data)
        instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for field in [
            "cash_party_name",
            "gross_weight",
            "tare_weight",
            "date_time_first",
            "date_time_second",
            "serial_no",
            "total_copy",
            "vehicle_no",
            "party_name",
            "vehicle_type",
            "purchaser",
            "seller",
            "party_mobile_no",
            "material",
        ]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance
