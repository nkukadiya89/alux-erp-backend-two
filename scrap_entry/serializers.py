"""
Scrap Entry serializers.
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from user.serializers import UserQuickSerializer

from .models import ScrapEntry, ScrapEntryItem, ScrapType, Process
from .services.scrap_entry_service import (
    create_scrap_entry,
    update_scrap_entry,
)


class ScrapEntryItemSerializer(serializers.ModelSerializer):
    """Read serializer for line items. Includes ScrapType and Process master refs."""

    item_code = serializers.CharField(source="item.item_code", read_only=True)
    item_name = serializers.CharField(source="item.item_name", read_only=True)
    scrap_type_code = serializers.CharField(source="scrap_type.code", read_only=True)
    scrap_type_name = serializers.CharField(source="scrap_type.name", read_only=True)
    uom_code = serializers.CharField(source="uom.uom_code", read_only=True)
    store_code = serializers.CharField(source="store.store_code", read_only=True)
    store_name = serializers.CharField(source="store.store_name", read_only=True)
    process_code = serializers.SerializerMethodField()
    process_name = serializers.SerializerMethodField()

    class Meta:
        model = ScrapEntryItem
        fields = [
            "id",
            "scrap_entry",
            "item",
            "item_code",
            "item_name",
            "scrap_type",
            "scrap_type_code",
            "scrap_type_name",
            "qty",
            "uom",
            "uom_code",
            "process",
            "process_code",
            "process_name",
            "from_process",
            "store",
            "store_code",
            "store_name",
            "batch_heat",
            "remarks",
        ]
        read_only_fields = ["scrap_entry"]

    def get_process_code(self, obj):
        return obj.process.code if obj.process_id else None

    def get_process_name(self, obj):
        return obj.process.name if obj.process_id else None


class ScrapEntryItemWriteSerializer(serializers.ModelSerializer):
    """Write serializer for line items (create/update). process = Process master FK (optional)."""

    class Meta:
        model = ScrapEntryItem
        fields = [
            "id",
            "item",
            "scrap_type",
            "qty",
            "uom",
            "process",
            "from_process",
            "store",
            "batch_heat",
            "remarks",
        ]

    def validate_qty(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(_("qty must be greater than 0."))
        return value


class ScrapEntryListSerializer(serializers.ModelSerializer):
    """List view: compact fields + audit names."""

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    plant_code = serializers.CharField(source="plant.plant_code", read_only=True)
    plant_name = serializers.CharField(source="plant.plant_name", read_only=True)
    source_department_name = serializers.SerializerMethodField()

    class Meta:
        model = ScrapEntry
        fields = [
            "id",
            "entry_no",
            "date",
            "plant",
            "plant_code",
            "plant_name",
            "source_department",
            "source_department_name",
            "source_ref",
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

    def get_source_department_name(self, obj):
        if obj.source_department:
            return obj.source_department.department_name
        return None


class ScrapEntryDetailSerializer(serializers.ModelSerializer):
    """Detail view: full fields + items + audit."""

    items = ScrapEntryItemSerializer(many=True, read_only=True)
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)
    plant_code = serializers.CharField(source="plant.plant_code", read_only=True)
    plant_name = serializers.CharField(source="plant.plant_name", read_only=True)
    source_department_name = serializers.SerializerMethodField()

    class Meta:
        model = ScrapEntry
        fields = [
            "id",
            "entry_no",
            "date",
            "plant",
            "plant_code",
            "plant_name",
            "source_department",
            "source_department_name",
            "source_ref",
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
            "entry_no",
            "total_qty",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_source_department_name(self, obj):
        if obj.source_department:
            return obj.source_department.department_name
        return None


class ScrapEntryWriteSerializer(serializers.ModelSerializer):
    """Create/update: nested items via service layer."""

    items = ScrapEntryItemWriteSerializer(many=True, required=True)

    class Meta:
        model = ScrapEntry
        fields = [
            "id",
            "entry_no",
            "date",
            "plant",
            "source_department",
            "source_ref",
            "remarks",
            "items",
        ]
        read_only_fields = ["entry_no"]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(_("At least one item is required."))
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return create_scrap_entry(validated_data, user)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return update_scrap_entry(instance, validated_data, user)


class ScrapEntryPostSerializer(serializers.Serializer):
    """Body for POST post (optional remarks)."""

    remarks = serializers.CharField(required=False, allow_blank=True)


class ScrapEntryTransferSerializer(serializers.Serializer):
    """Body for POST mark-transferred (optional)."""

    remarks = serializers.CharField(required=False, allow_blank=True)


class ScrapEntryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight for dropdown."""

    class Meta:
        model = ScrapEntry
        fields = ["id", "entry_no", "date", "plant", "status", "total_qty"]


# ----- ScrapType serializers -----
class ScrapTypeListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    category_code = serializers.CharField(
        source="category.category_code", read_only=True
    )
    category_name = serializers.CharField(
        source="category.category_name", read_only=True
    )

    class Meta:
        model = ScrapType
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_code",
            "category_name",
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


class ScrapTypeDetailSerializer(serializers.ModelSerializer):
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)
    category_code = serializers.CharField(
        source="category.category_code", read_only=True
    )
    category_name = serializers.CharField(
        source="category.category_name", read_only=True
    )

    class Meta:
        model = ScrapType
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_code",
            "category_name",
            "is_archived",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_detail",
            "updated_by_detail",
        ]


class ScrapTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapType
        fields = ["id", "code", "name", "category"]

    def validate_code(self, value):
        if value:
            return value.strip().upper()
        return value


class ScrapTypeDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapType
        fields = ["id", "code", "name"]


# ----- Process serializers -----
class ProcessListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Process
        fields = [
            "id",
            "code",
            "name",
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


class ProcessDetailSerializer(serializers.ModelSerializer):
    created_by_detail = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_detail = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = Process
        fields = [
            "id",
            "code",
            "name",
            "is_archived",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "created_by_detail",
            "updated_by_detail",
        ]


class ProcessWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ["id", "code", "name"]

    def validate_code(self, value):
        if value:
            return value.strip().upper()
        return value


class ProcessDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ["id", "code", "name"]
