from rest_framework import serializers

from common.models import UOM, YieldUnit
from user.serializers import UserQuickSerializer


class YieldUnitSerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)

    class Meta:
        model = YieldUnit
        fields = [
            "id",
            "name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class YieldUnitDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for YieldUnit dropdown API"""

    class Meta:
        model = YieldUnit
        fields = ["id", "name"]


class UOMSerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)

    class Meta:
        model = UOM
        fields = [
            "id",
            "uom_name",
            "uom_type",
            "decimal_allowed",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted",
        ]

    def validate_uom_type(self, value):
        """Validate uom_type choice"""
        if value not in [choice[0] for choice in UOM.UOMType.choices]:
            raise serializers.ValidationError(
                f"Invalid UOM type. Must be one of: {', '.join([choice[0] for choice in UOM.UOMType.choices])}"
            )
        return value


class UOMDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for UOM dropdown API - active and non-deleted only"""

    class Meta:
        model = UOM
        fields = ["id", "uom_name"]
