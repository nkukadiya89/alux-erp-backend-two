"""
Scrap Sale serializers.
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from user.serializers import UserQuickSerializer

from .models import ScrapSale, ScrapSaleItem
from .services.scrap_sale_service import (
    _get_available_qty,
    create_scrap_sale,
    update_scrap_sale,
)


class ScrapSaleItemSerializer(serializers.ModelSerializer):
    """Read serializer for line items; includes computed available_qty."""

    available_qty = serializers.SerializerMethodField()
    scrap_item_code = serializers.CharField(
        source="scrap_item.item_code", read_only=True
    )
    scrap_item_name = serializers.CharField(
        source="scrap_item.item_name", read_only=True
    )
    uom_code = serializers.CharField(source="uom.uom_code", read_only=True)

    class Meta:
        model = ScrapSaleItem
        fields = [
            "id",
            "scrap_sale",
            "scrap_item",
            "scrap_item_code",
            "scrap_item_name",
            "available_qty",
            "sale_qty",
            "uom",
            "uom_code",
            "rate",
            "total_value",
            "remarks",
        ]
        read_only_fields = ["scrap_sale", "total_value"]

    def get_available_qty(self, obj):
        if not obj.scrap_item_id:
            return "0"
        return str(_get_available_qty(obj.scrap_item_id))


class ScrapSaleItemWriteSerializer(serializers.ModelSerializer):
    """Write serializer for line items (create/update)."""

    class Meta:
        model = ScrapSaleItem
        fields = [
            "id",
            "scrap_item",
            "sale_qty",
            "uom",
            "rate",
            "total_value",
            "remarks",
        ]

    def validate_sale_qty(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(_("sale_qty must be greater than 0."))
        return value

    def validate(self, attrs):
        sale_qty = attrs.get("sale_qty")
        scrap_item_id = attrs.get("scrap_item")
        if scrap_item_id and sale_qty is not None:
            available = _get_available_qty(scrap_item_id)
            if sale_qty > available:
                raise serializers.ValidationError(
                    {
                        "sale_qty": _(
                            "sale_qty exceeds available scrap stock (%(avail)s)."
                        )
                        % {"avail": available}
                    }
                )
        rate = attrs.get("rate") or Decimal("0")
        if sale_qty is not None:
            attrs["total_value"] = (sale_qty * rate).quantize(Decimal("0.01"))
        return attrs


class ScrapSaleListSerializer(serializers.ModelSerializer):
    """List view: compact fields + audit names."""

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(
        source="customer.customer_name", read_only=True
    )

    class Meta:
        model = ScrapSale
        fields = [
            "id",
            "sale_no",
            "sale_date",
            "customer",
            "customer_name",
            "dispatch_ref",
            "remarks",
            "total_qty",
            "total_value",
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


class ScrapSaleDetailSerializer(serializers.ModelSerializer):
    """Detail view: full fields + items + audit."""

    items = ScrapSaleItemSerializer(many=True, read_only=True)
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)
    customer_name = serializers.CharField(
        source="customer.customer_name", read_only=True
    )

    class Meta:
        model = ScrapSale
        fields = [
            "id",
            "sale_no",
            "sale_date",
            "customer",
            "customer_name",
            "dispatch_ref",
            "remarks",
            "total_qty",
            "total_value",
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
            "sale_no",
            "total_qty",
            "total_value",
            "status",
            "created_at",
            "updated_at",
        ]


class ScrapSaleWriteSerializer(serializers.ModelSerializer):
    """Create/update: nested items via service layer."""

    items = ScrapSaleItemWriteSerializer(many=True, required=True)

    class Meta:
        model = ScrapSale
        fields = [
            "id",
            "sale_no",
            "sale_date",
            "customer",
            "dispatch_ref",
            "remarks",
            "items",
        ]
        read_only_fields = ["sale_no"]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(_("At least one item is required."))
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return create_scrap_sale(validated_data, user)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return update_scrap_sale(instance, validated_data, user)


class ScrapSaleFinalizeSerializer(serializers.Serializer):
    """Body for POST finalize (optional remarks)."""

    remarks = serializers.CharField(required=False, allow_blank=True)


class ScrapSaleCancelSerializer(serializers.Serializer):
    """Body for POST cancel (optional reason)."""

    reason = serializers.CharField(required=False, allow_blank=True)


class ScrapSaleDropdownSerializer(serializers.ModelSerializer):
    """Lightweight for dropdown; excludes archived."""

    class Meta:
        model = ScrapSale
        fields = ["id", "sale_no", "sale_date", "customer", "status", "total_value"]
