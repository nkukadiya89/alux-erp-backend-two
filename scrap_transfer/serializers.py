"""
Scrap Transfer serializers.
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from user.serializers import UserQuickSerializer

from .models import ScrapTransfer, ScrapTransferItem
from .services.scrap_transfer_service import (
    create_scrap_transfer,
    update_scrap_transfer,
    _get_available_scrap_qty,
)


class ScrapTransferItemSerializer(serializers.ModelSerializer):
    """Read serializer for line items. available_qty is computed from ScrapStoreStock."""

    item_code = serializers.CharField(source="scrap_item.item_code", read_only=True)
    item_name = serializers.CharField(source="scrap_item.item_name", read_only=True)
    uom_code = serializers.CharField(source="uom.uom_code", read_only=True)
    available_qty = serializers.SerializerMethodField()

    class Meta:
        model = ScrapTransferItem
        fields = [
            "id",
            "scrap_transfer",
            "scrap_item",
            "item_code",
            "item_name",
            "batch_heat",
            "available_qty",
            "transfer_qty",
            "uom",
            "uom_code",
            "remarks",
        ]
        read_only_fields = ["scrap_transfer"]

    def get_available_qty(self, obj):
        try:
            transfer = obj.scrap_transfer
            store_id = getattr(transfer, "from_store_id", None)
        except Exception:
            return None
        if store_id is None:
            return None
        return _get_available_scrap_qty(str(store_id), str(obj.scrap_item_id))


class ScrapTransferItemWriteSerializer(serializers.ModelSerializer):
    """Write serializer for line items (create/update)."""

    class Meta:
        model = ScrapTransferItem
        fields = [
            "id",
            "scrap_item",
            "batch_heat",
            "transfer_qty",
            "uom",
            "remarks",
        ]

    def validate_transfer_qty(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(_("transfer_qty must be greater than 0."))
        return value


class ScrapTransferListSerializer(serializers.ModelSerializer):
    """List view: compact fields + audit names."""

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    from_store_code = serializers.CharField(
        source="from_store.store_code", read_only=True
    )
    from_store_name = serializers.CharField(
        source="from_store.store_name", read_only=True
    )
    to_plant_code = serializers.CharField(source="to_plant.plant_code", read_only=True)
    to_plant_name = serializers.CharField(source="to_plant.plant_name", read_only=True)
    to_store_code = serializers.CharField(source="to_store.store_code", read_only=True)
    to_store_name = serializers.CharField(source="to_store.store_name", read_only=True)

    class Meta:
        model = ScrapTransfer
        fields = [
            "id",
            "transfer_no",
            "transfer_date",
            "from_store",
            "from_store_code",
            "from_store_name",
            "to_plant",
            "to_plant_code",
            "to_plant_name",
            "to_store",
            "to_store_code",
            "to_store_name",
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


class ScrapTransferDetailSerializer(serializers.ModelSerializer):
    """Detail view: full fields + items + audit."""

    items = ScrapTransferItemSerializer(many=True, read_only=True)
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)
    from_store_code = serializers.CharField(
        source="from_store.store_code", read_only=True
    )
    from_store_name = serializers.CharField(
        source="from_store.store_name", read_only=True
    )
    to_plant_code = serializers.CharField(source="to_plant.plant_code", read_only=True)
    to_plant_name = serializers.CharField(source="to_plant.plant_name", read_only=True)
    to_store_code = serializers.CharField(source="to_store.store_code", read_only=True)
    to_store_name = serializers.CharField(source="to_store.store_name", read_only=True)

    class Meta:
        model = ScrapTransfer
        fields = [
            "id",
            "transfer_no",
            "transfer_date",
            "from_store",
            "from_store_code",
            "from_store_name",
            "to_plant",
            "to_plant_code",
            "to_plant_name",
            "to_store",
            "to_store_code",
            "to_store_name",
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
            "transfer_no",
            "total_qty",
            "status",
            "created_at",
            "updated_at",
        ]


class ScrapTransferWriteSerializer(serializers.ModelSerializer):
    """Create/update: nested items via service layer."""

    items = ScrapTransferItemWriteSerializer(many=True, required=True)

    class Meta:
        model = ScrapTransfer
        fields = [
            "id",
            "transfer_no",
            "transfer_date",
            "from_store",
            "to_plant",
            "to_store",
            "remarks",
            "items",
        ]
        read_only_fields = ["transfer_no"]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(_("At least one item is required."))
        return value

    def validate(self, attrs):
        to_store = attrs.get("to_store") or (
            self.instance.to_store if self.instance else None
        )
        to_plant = attrs.get("to_plant") or (
            self.instance.to_plant if self.instance else None
        )
        if (
            to_store
            and to_plant
            and str(getattr(to_store, "plant_id", None))
            != str(getattr(to_plant, "id", None))
        ):
            raise serializers.ValidationError(
                {"to_store": _("to_store must belong to to_plant.")}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return create_scrap_transfer(validated_data, user)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return update_scrap_transfer(instance, validated_data, user)


class ScrapTransferSubmitSerializer(serializers.Serializer):
    """Body for POST submit (optional)."""

    remarks = serializers.CharField(required=False, allow_blank=True)


class ScrapTransferCompleteSerializer(serializers.Serializer):
    """Body for POST complete (optional)."""

    remarks = serializers.CharField(required=False, allow_blank=True)
