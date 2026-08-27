"""
Scrap Generation Remelt serializers.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from user.serializers import UserQuickSerializer

from .models import ScrapGenerationRemelt, ScrapGenerationRemeltItem
from .services.scrap_generation_remelt_service import (
    create_scrap_generation_remelt,
    update_scrap_generation_remelt,
)


class ScrapGenerationRemeltItemSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="item.item_code", read_only=True)
    item_name = serializers.CharField(source="item.item_name", read_only=True)
    uom_code = serializers.CharField(source="uom.uom_code", read_only=True)
    available_qty = serializers.SerializerMethodField()

    class Meta:
        model = ScrapGenerationRemeltItem
        fields = [
            "id",
            "scrap_generation_remelt",
            "item",
            "item_code",
            "item_name",
            "batch_heat",
            "available_qty",
            "qty",
            "uom",
            "uom_code",
            "remarks",
        ]
        read_only_fields = ["scrap_generation_remelt"]


class ScrapGenerationRemeltItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapGenerationRemeltItem
        fields = [
            "id",
            "item",
            "batch_heat",
            "qty",
            "uom",
            "remarks",
        ]

    def validate_qty(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(_("qty must be greater than 0."))
        return value


class ScrapGenerationRemeltListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    plant_code = serializers.CharField(source="plant.plant_code", read_only=True)
    plant_name = serializers.CharField(source="plant.plant_name", read_only=True)
    source_store_code = serializers.CharField(
        source="source_store.store_code", read_only=True
    )
    source_store_name = serializers.CharField(
        source="source_store.store_name", read_only=True
    )
    destination_store_code = serializers.CharField(
        source="destination_store.store_code", read_only=True
    )
    destination_store_name = serializers.CharField(
        source="destination_store.store_name", read_only=True
    )

    class Meta:
        model = ScrapGenerationRemelt
        fields = [
            "id",
            "remelt_no",
            "remelt_date",
            "plant",
            "plant_code",
            "plant_name",
            "source_store",
            "source_store_code",
            "source_store_name",
            "destination_store",
            "destination_store_code",
            "destination_store_name",
            "remarks",
            "total_qty",
            "status",
            "is_archived",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return (
                obj.created_by.get_full_name()
                or obj.created_by.email
                or str(obj.created_by)
            )
        return None

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return (
                obj.updated_by.get_full_name()
                or obj.updated_by.email
                or str(obj.updated_by)
            )
        return None


class ScrapGenerationRemeltDetailSerializer(serializers.ModelSerializer):
    items = ScrapGenerationRemeltItemSerializer(many=True, read_only=True)
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)
    plant_code = serializers.CharField(source="plant.plant_code", read_only=True)
    plant_name = serializers.CharField(source="plant.plant_name", read_only=True)
    source_store_code = serializers.CharField(
        source="source_store.store_code", read_only=True
    )
    source_store_name = serializers.CharField(
        source="source_store.store_name", read_only=True
    )
    destination_store_code = serializers.CharField(
        source="destination_store.store_code", read_only=True
    )
    destination_store_name = serializers.CharField(
        source="destination_store.store_name", read_only=True
    )

    class Meta:
        model = ScrapGenerationRemelt
        fields = [
            "id",
            "remelt_no",
            "remelt_date",
            "plant",
            "plant_code",
            "plant_name",
            "source_store",
            "source_store_code",
            "source_store_name",
            "destination_store",
            "destination_store_code",
            "destination_store_name",
            "remarks",
            "total_qty",
            "status",
            "is_archived",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_detail",
            "updated_by_detail",
            "items",
        ]
        read_only_fields = [
            "remelt_no",
            "total_qty",
            "status",
            "created_at",
            "updated_at",
        ]


class ScrapGenerationRemeltWriteSerializer(serializers.ModelSerializer):
    items = ScrapGenerationRemeltItemWriteSerializer(many=True, required=True)

    class Meta:
        model = ScrapGenerationRemelt
        fields = [
            "id",
            "remelt_no",
            "remelt_date",
            "plant",
            "source_store",
            "destination_store",
            "remarks",
            "items",
        ]
        read_only_fields = ["remelt_no"]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(_("At least one item is required."))
        return value

    def validate(self, attrs):
        source_store = attrs.get("source_store") or (
            self.instance.source_store if self.instance else None
        )
        destination_store = attrs.get("destination_store") or (
            self.instance.destination_store if self.instance else None
        )
        plant = attrs.get("plant") or (self.instance.plant if self.instance else None)
        if (
            source_store
            and destination_store
            and str(source_store.id) == str(destination_store.id)
        ):
            raise serializers.ValidationError(
                {"destination_store": _("destination_store must be different.")}
            )
        if (
            source_store
            and plant
            and str(getattr(source_store, "plant_id", None))
            != str(getattr(plant, "id", None))
        ):
            raise serializers.ValidationError(
                {"source_store": _("source_store must belong to plant.")}
            )
        if (
            destination_store
            and plant
            and str(getattr(destination_store, "plant_id", None))
            != str(getattr(plant, "id", None))
        ):
            raise serializers.ValidationError(
                {"destination_store": _("destination_store must belong to plant.")}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return create_scrap_generation_remelt(validated_data, user)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return update_scrap_generation_remelt(instance, validated_data, user)


class ScrapGenerationRemeltSubmitSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)


class ScrapGenerationRemeltCompleteSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)
