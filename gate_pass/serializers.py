from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from user.serializers import UserQuickSerializer

from .models import GatePass, GatePassItem
from .services import (
    create_gate_pass,
    update_gate_pass,
)


class GatePassItemSerializer(serializers.ModelSerializer):
    """Line items for read (detail/list/print)."""

    class Meta:
        model = GatePassItem
        fields = [
            "id",
            "gate_pass",
            "description",
            "unit",
            "qty",
            "purpose",
            "created_at",
        ]
        read_only_fields = ["gate_pass", "created_at"]

    def validate_qty(self, value: Decimal) -> Decimal:
        if value is None or value <= 0:
            raise serializers.ValidationError(_("Quantity must be greater than zero."))
        return value


class GatePassItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatePassItem
        fields = [
            "id",
            "description",
            "unit",
            "qty",
            "purpose",
        ]

    def validate_qty(self, value: Decimal) -> Decimal:
        if value is None or value <= 0:
            raise serializers.ValidationError(_("Quantity must be greater than zero."))
        return value


class GatePassListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GatePass
        fields = [
            "id",
            "gate_pass_no",
            "date",
            "type",
            "po_id",
            "party_name",
            "vehicle_no",
            "status",
            "is_archived",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "items_count",
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


class GatePassDetailSerializer(serializers.ModelSerializer):
    items = GatePassItemSerializer(many=True, read_only=True)
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = GatePass
        fields = [
            "id",
            "gate_pass_no",
            "date",
            "type",
            "po_id",
            "party_name",
            "vehicle_no",
            "remarks",
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
            "gate_pass_no",
            "status",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]


class GatePassWriteSerializer(serializers.ModelSerializer):
    items = GatePassItemWriteSerializer(many=True)

    class Meta:
        model = GatePass
        fields = [
            "id",
            "gate_pass_no",
            "date",
            "type",
            "po_id",
            "party_name",
            "vehicle_no",
            "remarks",
            "status",
            "items",
        ]
        read_only_fields = [
            "gate_pass_no",
            "status",
        ]

    def validate(self, attrs):
        if not attrs.get("items"):
            raise serializers.ValidationError(
                {"items": [_("At least one item is required.")]}
            )

        instance = self.instance
        new_type = attrs.get("type") or (instance and instance.type)

        if instance:
            if instance.status == GatePass.STATUS_CLOSED:
                raise serializers.ValidationError(
                    _("Closed gate pass cannot be modified.")
                )
            if instance.type != new_type:
                raise serializers.ValidationError(
                    _("Gate pass type cannot be changed once created.")
                )

        # When PO is attached, description editing should be locked at item level.
        # We enforce that in service layer by disallowing description changes
        # for existing items when gate_pass.po is set.
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return create_gate_pass(validated_data, user)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return update_gate_pass(instance, validated_data, user)


class GatePassDropdownSerializer(serializers.ModelSerializer):
    """Lightweight for dropdown; archived excluded in view."""

    class Meta:
        model = GatePass
        fields = [
            "id",
            "gate_pass_no",
            "type",
            "status",
            "date",
            "party_name",
        ]


class GatePassPrintSerializer(serializers.ModelSerializer):
    """Serializer for print-data API."""

    items = GatePassItemSerializer(many=True, read_only=True)
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)

    class Meta:
        model = GatePass
        fields = [
            "id",
            "gate_pass_no",
            "date",
            "type",
            "po_id",
            "party_name",
            "vehicle_no",
            "remarks",
            "status",
            "items",
            "created_at",
            "created_by",
            "created_by_detail",
        ]
