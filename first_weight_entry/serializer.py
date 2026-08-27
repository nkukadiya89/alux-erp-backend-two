from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import serializers
from common.serializers import BaseModelSerializer
from transporter.models import Transporter
from vehicle_master.models import VehicleMaster
from .models import FirstWeightEntry

User = get_user_model()


class FirstWeightEntrySerializer(BaseModelSerializer):
    capture_photo = serializers.CharField(
        required=False, allow_null=True, read_only=True
    )
    capture_photo_2 = serializers.CharField(
        required=False, allow_null=True, read_only=True
    )
    party_name = serializers.PrimaryKeyRelatedField(
        queryset=Transporter.objects.filter(deleted=False, is_active="active"),
        required=False,
        allow_null=True,
    )
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
        model = FirstWeightEntry
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "weight_for",
            "weight_automatic",
            "cash_party_name",
            "gross_weight",
            "tare_weight",
            "net_weight",
            "date_time_first",
            "date_time_second",
            "is_second_entry_done",
            "mound",
            "serial_no",
            "total_copy",
            "vehicle_no",
            "vehicle_no_display",
            "vehicle_type",
            "vehicle_type_name",
            "capture_photo",
            "capture_photo_2",
            "party_name",
            "party_name_display",
            "purchaser",
            "purchaser_name",
            "seller",
            "seller_name",
            "party_mobile_no",
            "material",
            "material_name",
        ]

    def validate(self, validated_data):
        instance = getattr(self, "instance", None)

        vehicle_no = validated_data.get(
            "vehicle_no", instance.vehicle_no if instance else None
        )
        transporter = validated_data.get(
            "party_name", instance.party_name if instance else None
        )

        if vehicle_no and transporter:
            qs = FirstWeightEntry.objects.filter(
                vehicle_no=vehicle_no,
                party_name=transporter,
                is_second_entry_done=False,
                deleted=False,
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "vehicle_no": "First weight entry already exists for this Transporter Name and Vehicle No. Please complete the Second weight entry before creating a new Entry"
                    }
                )
        return validated_data

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        instance = FirstWeightEntry.objects.create(**validated_data)
        if user is not None:
            instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        fields_to_update = [
            "weight_for",
            "cash_party_name",
            "weight_automatic",
            "gross_weight",
            "net_weight",
            "tare_weight",
            "date_time_first",
            "date_time_second",
            "mound",
            "serial_no",
            "total_copy",
            "vehicle_no",
            "vehicle_type",
            "party_name",
            "purchaser",
            "party_mobile_no",
            "material",
            "is_second_entry_done",
        ]

        for field in fields_to_update:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user is not None:
            instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance
