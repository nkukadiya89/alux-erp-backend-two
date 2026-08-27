from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from common.models import Plant
from common.serializers import BaseModelSerializer
from store.models import Store
from user.serializers import UserQuickSerializer


class BaseSerializer(serializers.ModelSerializer):
    def run_validation(self, data):
        """Override validation to customize error messages for required fields."""
        try:
            return super().run_validation(data)
        except serializers.ValidationError as e:
            error_detail = e.detail

            if isinstance(error_detail, dict):
                for field, messages in error_detail.items():
                    if (
                        isinstance(messages, list)
                        and "This field is required." in messages
                    ):
                        error_detail[field] = [f"{field} is required."]

            raise serializers.ValidationError(error_detail)


class StoreSerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    plant_code = serializers.CharField(source="plant.plant_code", read_only=True)
    plant_name = serializers.CharField(source="plant.plant_name", read_only=True)
    store_type_name = serializers.CharField(source="store_type.name", read_only=True)

    class Meta:
        model = Store
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "store_code",
            "store_name",
            "store_type",
            "store_type_name",
            "plant",
            "plant_code",
            "plant_name",
            "allows_negative_stock",
        ]
        read_only_fields = [
            "id",
            "plant_code",
            "plant_name",
        ]

    def validate_store_code(self, value):
        """Case-insensitive unique validation for store_code"""
        if value:
            value = value.strip()
            queryset = Store.objects.filter(store_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Store code already exists.")
        return value


class StoreDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Store dropdown API - active and non-archived only"""

    class Meta:
        model = Store
        fields = ["id", "store_code", "store_name"]
