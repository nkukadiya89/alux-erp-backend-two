from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import serializers
from common.serializers import BaseModelSerializer
from vehicle_master.models import VehicleMaster
from .models import SecondWeightEntry

User = get_user_model()


class SecondWeightEntrySerializer(BaseModelSerializer):
    capture_photo_second_1 = serializers.CharField(
        required=False, allow_null=True, read_only=True
    )
    capture_photo_second_2 = serializers.CharField(
        required=False, allow_null=True, read_only=True
    )
    party_name_display = serializers.CharField(
        source="party_name.party_name", read_only=True
    )
    vehicle_type_name = serializers.CharField(
        source="vehicle_type.vehicle_type", read_only=True
    )
    material_name = serializers.CharField(source="material.item_name", read_only=True)
    first_weight_entry_display = serializers.CharField(
        source="first_weight_entry.serial_no", read_only=True
    )

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
    capture_photo = serializers.CharField(
        source="first_weight_entry.capture_photo", read_only=True
    )
    capture_photo_2 = serializers.CharField(
        source="first_weight_entry.capture_photo_2", read_only=True
    )
    seller_name = serializers.CharField(source="seller.get_full_name", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = SecondWeightEntry
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "first_weight_entry",
            "first_weight_entry_display",
            "weight_for",
            "weight_automatic",
            "cash_party_name",
            "gross_weight",
            "tare_weight",
            "net_weight",
            "date_time_first",
            "date_time_second",
            "mound",
            "serial_no",
            "is_same_weight_allowed",
            "total_copy",
            "vehicle_no",
            "vehicle_no_display",
            "vehicle_type",
            "capture_photo",
            "capture_photo_2",
            "capture_photo_second_1",
            "capture_photo_second_2",
            "vehicle_type_name",
            "party_name",
            "party_name_display",
            "purchaser",
            "purchaser_name",
            "party_mobile_no",
            "material",
            "material_name",
            "seller",
            "seller_name",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        first_entry = validated_data.get("first_weight_entry")

        instance = SecondWeightEntry(**validated_data)
        if user is not None:
            instance.created_by = user
        instance.created_at = now()
        instance.save()
        if first_entry:
            first_entry.is_second_entry_done = True
            first_entry.save(update_fields=["is_second_entry_done"])
        return instance

    def update(self, instance, validated_data):
        old_first_entry = instance.first_weight_entry
        for field in [
            "first_weight_entry",
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
            "seller",
            "party_mobile_no",
            "material",
            "is_same_weight_allowed",
        ]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user is not None:
            instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        new_first_entry = instance.first_weight_entry

        if old_first_entry and old_first_entry != new_first_entry:
            old_first_entry.is_second_entry_done = False
            old_first_entry.save(update_fields=["is_second_entry_done"])

        if new_first_entry:
            new_first_entry.is_second_entry_done = True
            new_first_entry.save(update_fields=["is_second_entry_done"])

        return instance

    def validate(self, data):
        instance = getattr(self, "instance", None)

        first_entry = data.get("first_weight_entry")
        if not first_entry and instance:
            first_entry = instance.first_weight_entry
        if not first_entry:
            raise serializers.ValidationError("First weight entry is required")

        second_weight_for = data.get(
            "weight_for", instance.weight_for if instance else None
        )

        is_same_allowed = data.get(
            "is_same_weight_allowed",
            instance.is_same_weight_allowed if instance else False,
        )

        first_weight_for = first_entry.weight_for
        if second_weight_for == "gross weight":
            gross_weight = data.get(
                "gross_weight", instance.gross_weight if instance else None
            )
            if gross_weight is None:
                raise serializers.ValidationError(
                    {"gross_weight": "Gross weight is required"}
                )
        if second_weight_for == "tare weight":
            tare_weight = data.get(
                "tare_weight", instance.tare_weight if instance else None
            )
            if tare_weight is None:
                raise serializers.ValidationError(
                    {"tare_weight": "Tare weight is required"}
                )
        if not is_same_allowed:
            if first_weight_for == second_weight_for:
                raise serializers.ValidationError(
                    {
                        "weight_for": "weight_for choice must be opposite of first weight entry when is_same_weight_allowed is False"
                    }
                )
        if is_same_allowed:
            if first_weight_for != second_weight_for:
                raise serializers.ValidationError(
                    {
                        "is_same_weight_allowed": "You can enable this only when both first_weight_entry and second_weight_entry have the same weight_for"
                    }
                )

        qs = SecondWeightEntry.objects.filter(first_weight_entry=first_entry)
        if instance:
            qs = qs.exclude(id=instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                {
                    "first_weight_entry": "Second entry already exists for this first entry"
                }
            )
        return data
