from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import VehicleMaster


class VehicleMasterSerializer(BaseModelSerializer):
    party_name_display = serializers.CharField(
        source="party_name.party_name", read_only=True
    )
    vehicle_type_display = serializers.CharField(
        source="vehicle_type.vehicle_type", read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = VehicleMaster
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "party_name",
            "party_name_display",
            "vehicle_no",
            "vehicle_type",
            "vehicle_type_display",
            "tare_wt",
        ]

    def validate_vehicle_no(self, value):
        if value:
            value = value.strip().upper()
            qs = VehicleMaster.objects.filter(vehicle_no__iexact=value, deleted=False)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Vehicle number already exists.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.deleted:
            raise serializers.ValidationError("Cannot edit an archived vehicle.")
        return attrs


class VehicleMasterListSerializer(BaseModelSerializer):
    party_name_display = serializers.CharField(
        source="party_name.party_name", read_only=True
    )
    vehicle_type_display = serializers.CharField(
        source="vehicle_type.vehicle_type", read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = VehicleMaster
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "vehicle_no",
            "party_name",
            "party_name_display",
            "vehicle_type",
            "vehicle_type_display",
            "tare_wt",
        ]

class VehicleMasterDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMaster
        fields = ["id", "vehicle_no"]


class VehicleMasterSortSerializer(serializers.ModelSerializer):
    party_name_display = serializers.CharField(
        source="party_name.party_name", read_only=True
    )

    class Meta:
        model = VehicleMaster
        fields = ["id", "vehicle_no", "party_name_display"]
