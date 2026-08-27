from rest_framework import serializers

from common.master_serializers import UOMDropdownSerializer
from common.serializers import UserQuickSerializer

from .models import (
    AdditiveCategory,
    AdditiveMaster,
    FuelType,
    Furnace,
    FurnaceType,
    MaterialType,
    RecoveryStandard,
)


class MaterialTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialType
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value):
        if value:
            value = value.strip().upper()
            qs = MaterialType.objects.filter(code__iexact=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Material type with this code already exists."
                )
        return value

    def validate_name(self, value):
        if not (value and value.strip()):
            raise serializers.ValidationError("Name is required.")
        return value.strip()


class MaterialTypeDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialType
        fields = ["id", "code", "name"]


class FurnaceTypeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for FurnaceType dropdown API - active and non-archived only"""

    class Meta:
        model = FurnaceType
        fields = ["id", "name"]


class FuelTypeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for FuelType dropdown API - active and non-archived only"""

    class Meta:
        model = FuelType
        fields = ["id", "name"]


class FurnaceSerializer(serializers.ModelSerializer):
    """Serializer for Furnace model"""

    furnace_type_info = FurnaceTypeDropdownSerializer(
        source="furnace_type", read_only=True
    )
    fuel_type_info = FuelTypeDropdownSerializer(source="fuel_type", read_only=True)

    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = Furnace
        fields = [
            "id",
            "furnace_code",
            "furnace_name",
            "furnace_type",
            "furnace_type_info",
            "furnace_capacity",
            "fuel_type",
            "fuel_type_info",
            "min_temperature",
            "max_temperature",
            "status",
            "remark",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_info",
            "updated_by",
            "updated_by_info",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def validate_furnace_code(self, value):
        """Case-insensitive unique validation for furnace_code"""
        if value:
            value = value.strip().upper()
            queryset = Furnace.objects.filter(furnace_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Furnace code already exists.")
        return value

    def validate(self, attrs):
        """Additional validation"""
        # Cannot edit archived furnaces
        if self.instance and self.instance.status == "Inactive":
            raise serializers.ValidationError("Cannot edit archived furnace.")

        # Check if can deactivate
        if attrs.get("status") == "Inactive" and self.instance:
            from melting_furnace.services.furnace_service import can_deactivate_furnace

            can_deactivate, message = can_deactivate_furnace(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"status": message})

        return attrs


class FurnaceDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Furnace dropdown API - active and non-archived only"""

    class Meta:
        model = Furnace
        fields = ["id", "furnace_code", "furnace_name"]


class AdditiveCategoryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for AdditiveCategory dropdown API - active and non-archived only"""

    class Meta:
        model = AdditiveCategory
        fields = ["id", "name"]


class AdditiveMasterSerializer(serializers.ModelSerializer):
    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)
    category_info = AdditiveCategoryDropdownSerializer(
        source="category", read_only=True
    )
    unit_info = UOMDropdownSerializer(source="unit", read_only=True)

    class Meta:
        model = AdditiveMaster
        fields = [
            "id",
            "additive_code",
            "additive_name",
            "category",
            "category_info",
            "unit",
            "unit_info",
            "standard_quantity",
            "min_limit",
            "max_limit",
            "status",
            "remarks",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_info",
            "updated_by",
            "updated_by_info",
            "f_id",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def validate_additive_code(self, value):
        """Case-insensitive unique validation for furnace_code"""
        if value:
            value = value.strip().upper()
            queryset = AdditiveMaster.objects.filter(additive_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Additive code already exists.")
        return value

    def validate(self, attrs):
        """Additional validation"""
        # Cannot edit archived furnaces
        if self.instance and self.instance.status == "Inactive":
            raise serializers.ValidationError("Cannot edit archived furnace.")

        # Check if can deactivate
        if attrs.get("status") == "Inactive" and self.instance:
            from melting_furnace.services.additive_master_service import (
                can_deactivate_additive_master,
            )

            can_deactivate, message = can_deactivate_additive_master(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"status": message})

        return attrs


class AdditiveMasterDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Furnace dropdown API - active and non-archived only"""

    class Meta:
        model = AdditiveMaster
        fields = ["id", "additive_code", "additive_name"]


class RecoveryStandardSerializer(serializers.ModelSerializer):
    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)
    furnace_type_info = FurnaceTypeDropdownSerializer(
        source="furnace_type", read_only=True
    )
    material_type_info = MaterialTypeDropdownSerializer(
        source="material_type", read_only=True
    )

    class Meta:
        model = RecoveryStandard
        fields = [
            "id",
            "furnace_type",
            "furnace_type_info",
            "material_type",
            "material_type_info",
            "min_recovery",
            "max_recovery",
            "standard_loss",
            "effective_from",
            "status",
            "remarks",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_info",
            "updated_by",
            "updated_by_info",
            "f_id",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def validate_min_recovery(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Min recovery must be between 0 and 100.")
        return value

    def validate_max_recovery(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Max recovery must be between 0 and 100.")
        return value

    def validate_standard_loss(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(
                "Standard loss must be between 0 and 100."
            )
        return value

    def validate(self, attrs):
        min_r = attrs.get("min_recovery", getattr(self.instance, "min_recovery", None))
        max_r = attrs.get("max_recovery", getattr(self.instance, "max_recovery", None))
        if min_r is not None and max_r is not None and min_r > max_r:
            raise serializers.ValidationError(
                {"max_recovery": "Max recovery must be >= min recovery."}
            )
        return attrs


class RecoveryStandardDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecoveryStandard
        fields = ["id", "furnace_type", "material_type"]
