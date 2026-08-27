from rest_framework import serializers

from user.serializers import UserQuickSerializer
from vendor.models import Vendor
from transporter.models import Transporter

from .models import GateEntry, GateEntryItem
from .services import create_gate_entry, update_gate_entry


class VendorMinimalSerializer(serializers.ModelSerializer):
    """Minimal vendor for Gate Entry dropdown/display."""

    class Meta:
        model = Vendor
        fields = ["id", "person_name", "vendor_registered_name", "vendor_trade_name"]


class TransporterMinimalSerializer(serializers.ModelSerializer):
    """Minimal transporter for Gate Entry dropdown/display."""

    class Meta:
        model = Transporter
        fields = ["id", "party_name", "party_code"]


class GateEntryItemSerializer(serializers.ModelSerializer):
    """Line items for read (detail/list)."""

    class Meta:
        model = GateEntryItem
        fields = ["id", "description", "unit", "qty", "purpose", "created_at"]

    def validate_qty(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class GateEntryItemWriteSerializer(serializers.ModelSerializer):
    """Line items for create/update (no gate_entry in input)."""

    class Meta:
        model = GateEntryItem
        fields = ["id", "description", "unit", "qty", "purpose"]

    def validate_qty(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class GateEntryDetailSerializer(serializers.ModelSerializer):
    """Full read serializer for retrieve (with nested items)."""

    vendor_info = VendorMinimalSerializer(source="vendor", read_only=True)
    transporter_info = TransporterMinimalSerializer(
        source="transporter", read_only=True
    )
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)
    items = GateEntryItemSerializer(many=True, read_only=True)

    class Meta:
        model = GateEntry
        fields = [
            "id",
            "gate_entry_no",
            "date",
            "vendor",
            "vendor_info",
            "driver_name",
            "transporter",
            "transporter_info",
            "driver_mobile_no",
            "vehicle_no",
            "challan_no",
            "invoice_no",
            "inward_time",
            "outward_time",
            "empty_vehicle_weight",
            "status",
            "is_archived",
            "created_by",
            "updated_by",
            "created_by_detail",
            "updated_by_detail",
            "created_at",
            "updated_at",
            "deleted",
            "items",
        ]
        read_only_fields = [
            "gate_entry_no",
            "created_at",
            "created_by",
            "updated_by",
        ]


class GateEntryWriteSerializer(serializers.ModelSerializer):
    """Create/update serializer; delegates to services."""

    items = GateEntryItemWriteSerializer(many=True)

    class Meta:
        model = GateEntry
        fields = [
            "id",
            "gate_entry_no",
            "date",
            "vendor",
            "driver_name",
            "transporter",
            "driver_mobile_no",
            "vehicle_no",
            "challan_no",
            "invoice_no",
            "inward_time",
            "outward_time",
            "empty_vehicle_weight",
            "status",
            "items",
        ]
        read_only_fields = ["gate_entry_no"]

    def validate(self, attrs):
        instance = self.instance
        items = attrs.get("items", None)
        if instance is None:
            if not items:
                raise serializers.ValidationError(
                    {"items": ["At least one item is required."]}
                )
        else:
            if items is not None and not items:
                raise serializers.ValidationError(
                    {"items": ["At least one item is required."]}
                )
        status = attrs.get("status") or (instance and instance.status)
        if status == GateEntry.STATUS_CLOSE:
            empty_weight = attrs.get("empty_vehicle_weight") or (
                instance and instance.empty_vehicle_weight
            )
            if empty_weight is None:
                raise serializers.ValidationError(
                    {
                        "empty_vehicle_weight": "Empty vehicle weight is required before closing."
                    }
                )
            out_time = attrs.get("outward_time") or (instance and instance.outward_time)
            if out_time is None:
                raise serializers.ValidationError(
                    {"outward_time": "Outward time is required before closing."}
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return create_gate_entry(validated_data, user)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return update_gate_entry(instance, validated_data, user)


class GateEntryListSerializer(serializers.ModelSerializer):
    """List serializer with minimal nested info."""

    vendor_name = serializers.CharField(source="vendor.person_name", read_only=True)
    transporter_name = serializers.CharField(
        source="transporter.party_name", read_only=True, default=None
    )
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GateEntry
        fields = [
            "id",
            "gate_entry_no",
            "date",
            "vendor",
            "vendor_name",
            "driver_name",
            "transporter",
            "transporter_name",
            "driver_mobile_no",
            "vehicle_no",
            "challan_no",
            "invoice_no",
            "inward_time",
            "outward_time",
            "empty_vehicle_weight",
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
                or getattr(obj.created_by, "email", None)
                or str(obj.created_by)
            )
        return None

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return (
                obj.updated_by.get_full_name()
                or getattr(obj.updated_by, "email", None)
                or str(obj.updated_by)
            )
        return None


class GateEntryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight for dropdown; archived excluded in view."""

    class Meta:
        model = GateEntry
        fields = ["id", "gate_entry_no", "date", "status", "vehicle_no"]
