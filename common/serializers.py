from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils import timezone
from rest_framework import serializers

from common.models import (
    Country,
    Currency,
    Department,
    FinancialYearModel,
    GstType,
    ItemCategory,
    JobWorkType,
    PackingMode,
    Plant,
    PlantCapability,
    PlantType,
    PlantTypeCapability,
    SectionType,
    StoreType,
)
from user.serializers import UserQuickSerializer


class BaseModelSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)

    class Meta:
        model = None
        fields = [
            "id",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

        kwargs = {
            "created_by": {"read_only": True},
            "updated_by": {"read_only": True},
            "deleted_by": {"read_only": True},
        }


class BaseModelListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.first_name", read_only=True)
    updated_by = serializers.CharField(source="updated_by.first_name", read_only=True)
    deleted_by = serializers.CharField(source="deleted_by.first_name", read_only=True)

    class Meta:
        model = None
        fields = [
            "id",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

        kwargs = {
            "created_by": {"read_only": True},
            "updated_by": {"read_only": True},
            "deleted_by": {"read_only": True},
        }


class CountrySerializers(serializers.ModelSerializer):
    f_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Country
        fields = [
            "id",
            "f_id",
            "name",
            "code",
            "unicode",
            "country_flag",
            "created_by",
            "updated_by",
            "deleted",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


class CurrencySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", required=False)
    f_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Currency
        fields = [
            "id",
            "f_id",
            "country",
            "country_name",
            "currency_name",
            "currency_code",
            "currency_symbol",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate_currency_name(self, value):
        if Currency.objects.filter(currency_name=value).exists():
            raise serializers.ValidationError("Currency name already exists")
        return value


class GstTypeSerializer(serializers.ModelSerializer):
    f_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GstType
        fields = ["id", "name", "full_name", "percentage", "f_id"]


class JobWorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobWorkType
        fields = ["id", "name"]

    def validate_name(self, value):
        if JobWorkType.objects.filter(name=value).exists():
            raise serializers.ValidationError("Jobwork name already exists")
        return value


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYearModel
        fields = [
            "fid",
            "financial_year",
            "start_date",
            "end_date",
            "default",
            "current",
        ]


class PackingModeSerializers(BaseModelSerializer):

    class Meta(BaseModelSerializer.Meta):
        model = PackingMode
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "code",
            "name",
            "description",
            "price_per_kg",
        ]

    def validate_name(self, value):
        """Validate name uniqueness (case-insensitive)"""
        if value:
            queryset = PackingMode.objects.filter(name__iexact=value, deleted=False)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "A packing mode with this name already exists."
                )
        return value

    def validate_code(self, value):
        """Validate code uniqueness"""
        if value:
            queryset = PackingMode.objects.filter(code__iexact=value, deleted=False)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "A packing mode with this code already exists."
                )
        return value


class PackingModeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for PackingMode dropdown API - active and non-archived only"""

    class Meta:
        model = PackingMode
        fields = ["id", "name"]


# Alias for backward compatibility
PackingModeSerializer = PackingModeSerializers


class PackingModeSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackingMode
        fields = [
            "id",
            "name",
        ]


class PlantSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    plant_type_code = serializers.CharField(source="plant_type.code", read_only=True)
    plant_type_name = serializers.CharField(source="plant_type.name", read_only=True)
    plant_head_info = UserQuickSerializer(source="plant_head", read_only=True)

    class Meta:
        model = Plant
        fields = [
            "id",
            "plant_code",
            "plant_name",
            "plant_type",
            "plant_type_code",
            "plant_type_name",
            "status",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "country",
            "postal_code",
            "phone_number",
            "email",
            "plant_head",
            "plant_head_info",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted",
            "deleted_at",
            "deleted_by",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "deleted",
            "plant_head_info",
        ]

    def validate_plant_code(self, value):
        """Case-insensitive unique validation for plant_code"""
        if value:
            value = value.strip().upper()
            queryset = Plant.objects.filter(plant_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Plant code already exists.")
        return value

    def validate_email(self, value):
        """Email format validation"""
        if value:
            validator = EmailValidator()
            try:
                validator(value)
            except ValidationError:
                raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate_phone_number(self, value):
        """Phone number length validation"""
        if value:
            cleaned = (
                value.replace("-", "")
                .replace(" ", "")
                .replace("(", "")
                .replace(")", "")
            )
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise serializers.ValidationError(
                    "Phone number must be between 10 and 15 digits."
                )
        return value

    def validate(self, attrs):
        """Additional validation"""
        if attrs.get("status") == "Inactive" and self.instance:
            # Check if plant can be deactivated using service function
            from common.services.plant_service import can_deactivate_plant

            can_deactivate, message = can_deactivate_plant(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"status": message})
        return attrs


class PlantListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list view - optimized for performance
    Includes only essential fields needed for table/list display
    Reduces response size and serialization overhead by ~60%
    """

    plant_type_code = serializers.CharField(source="plant_type.code", read_only=True)
    plant_type_name = serializers.CharField(source="plant_type.name", read_only=True)
    plant_head_info = UserQuickSerializer(source="plant_head", read_only=True)

    class Meta:
        model = Plant
        fields = [
            "id",
            "plant_code",
            "plant_name",
            "plant_type",
            "plant_type_code",
            "plant_type_name",
            "status",
            "city",
            "plant_head",
            "plant_head_info",
            "created_at",
        ]
        read_only_fields = fields


class PlantDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown API"""

    class Meta:
        model = Plant
        fields = ["id", "plant_code", "plant_name"]


class PlantTypeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Plant Type dropdown API"""

    class Meta:
        model = PlantType
        fields = ["id", "code", "name"]


class PlantTypeSerializer(serializers.ModelSerializer):
    """Serializer for PlantType model"""

    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = PlantType
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "code",
            "name",
            "status",
            "is_deleted",
            "created_by_info",
            "updated_by_info",
            "capabilities",
        ]
        read_only_fields = [
            "id",
            "is_deleted",
            "created_by",
            "updated_by",
            "capabilities",
        ]
        extra_kwargs = {
            "code": {
                "validators": []  # Remove automatic UniqueValidator to prevent duplicate error messages
            }
        }

    def get_capabilities(self, obj):
        """Get active, non-deleted capabilities for the plant type"""
        # Use prefetched active_capabilities if available, otherwise query
        if hasattr(obj, "active_capabilities"):
            capabilities = obj.active_capabilities
        else:
            capabilities = obj.capabilities.filter(
                status="Active", is_deleted=False
            ).select_related("capability")
        return PlantTypeCapabilityListSerializer(capabilities, many=True).data

    def validate_code(self, value):
        """Case-insensitive unique validation for code"""
        if value:
            value = value.strip().upper()

            queryset = PlantType.objects.filter(code__iexact=value, is_deleted=False)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "plant type with this code already exists."
                )
        return value


class PlantCapabilitySerializer(serializers.ModelSerializer):
    """Serializer for PlantCapability model"""

    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = PlantCapability
        fields = [
            "id",
            "code",
            "name",
            "description",
            "status",
            "created_at",
            "updated_at",
            "is_deleted",
            "created_by",
            "created_by_info",
            "updated_by",
            "updated_by_info",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "is_deleted",
            "created_by",
            "updated_by",
        ]

    def validate_code(self, value):
        """Case-insensitive unique validation for code"""
        if value:
            value = value.strip().upper()
            # Only check for existing non-deleted records with the same code
            # This prevents duplicate error messages with database constraints
            queryset = PlantCapability.objects.filter(
                code__iexact=value, is_deleted=False
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Capability code already exists.")
        return value


class PlantTypeCapabilitySerializer(serializers.ModelSerializer):
    """Serializer for PlantTypeCapability mapping"""

    plant_type_code = serializers.CharField(source="plant_type.code", read_only=True)
    plant_type_name = serializers.CharField(source="plant_type.name", read_only=True)
    capability_code = serializers.CharField(source="capability.code", read_only=True)
    capability_name = serializers.CharField(source="capability.name", read_only=True)
    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = PlantTypeCapability
        fields = [
            "id",
            "plant_type",
            "plant_type_code",
            "plant_type_name",
            "capability",
            "capability_code",
            "capability_name",
            "status",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_info",
            "updated_by",
            "updated_by_info",
            "is_deleted",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "is_deleted",
        ]

    def validate(self, attrs):
        """Validate mapping constraints"""
        plant_type = attrs.get("plant_type") or (
            self.instance.plant_type if self.instance else None
        )
        capability = attrs.get("capability") or (
            self.instance.capability if self.instance else None
        )

        if not plant_type or not capability:
            raise serializers.ValidationError("Plant type and capability are required.")

        # Check if plant type is active
        if plant_type.is_deleted:
            raise serializers.ValidationError(
                "Cannot assign capability to deleted plant type."
            )

        # Check if capability is active
        if capability.is_deleted or capability.status != "Active":
            raise serializers.ValidationError(
                "Cannot assign inactive or deleted capability."
            )

        # Check for duplicate mapping
        queryset = PlantTypeCapability.objects.filter(
            plant_type=plant_type, capability=capability, is_deleted=False
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "This capability is already assigned to this plant type."
            )

        # Check if deactivating mapping with active plants
        if attrs.get("status") == "Inactive" and self.instance:
            from common.services.plant_capability_service import (
                can_deactivate_capability_mapping,
            )

            can_deactivate, message = can_deactivate_capability_mapping(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"status": message})

        return attrs


class PlantTypeCapabilityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing capabilities of a plant type"""

    capability_code = serializers.CharField(source="capability.code", read_only=True)
    capability_name = serializers.CharField(source="capability.name", read_only=True)

    class Meta:
        model = PlantTypeCapability
        fields = [
            "id",
            "capability",
            "capability_code",
            "capability_name",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class SectionQuickSerializer(serializers.ModelSerializer):

    class Meta:
        model = SectionType
        fields = ["id", "name"]


class SectionTypeSerializer(serializers.ModelSerializer):
    """Serializer for SectionType model"""

    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = SectionType
        fields = [
            "id",
            "name",
            "is_active",
            "is_archived",
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
            "is_archived",
            "created_by",
            "updated_by",
        ]

    def validate_name(self, value):
        """Case-insensitive unique validation for name"""
        if value:
            value = value.strip()
            queryset = SectionType.objects.filter(name__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.filter(is_archived=False).exists():
                raise serializers.ValidationError("Section type name already exists.")
        return value

    def validate(self, attrs):
        """Additional validation"""
        # Cannot edit archived section types
        if self.instance and self.instance.is_archived:
            raise serializers.ValidationError("Cannot edit archived section type.")

        # Check if can deactivate (future-safe for transaction validation)
        if attrs.get("is_active") == False and self.instance:
            from common.services.section_type_service import can_deactivate_section_type

            can_deactivate, message = can_deactivate_section_type(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"is_active": message})
        return attrs


class SectionTypeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Section Type dropdown API - active and non-archived only"""

    class Meta:
        model = SectionType
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""

    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)
    plant_code = serializers.CharField(
        source="plant.plant_code", read_only=True, allow_null=True
    )
    plant_name = serializers.CharField(
        source="plant.plant_name", read_only=True, allow_null=True
    )
    parent_department_code = serializers.CharField(
        source="parent_department.department_code", read_only=True
    )
    parent_department_name = serializers.CharField(
        source="parent_department.department_name", read_only=True
    )

    class Meta:
        model = Department
        fields = [
            "id",
            "department_code",
            "department_name",
            "department_type",
            "plant",
            "plant_code",
            "plant_name",
            "cost_center_code",
            "parent_department",
            "parent_department_code",
            "parent_department_name",
            "status",
            "is_archived",
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
            "is_archived",
            "created_by",
            "updated_by",
        ]

    def validate_department_code(self, value):
        """Case-insensitive unique validation for department_code"""
        if value:
            value = value.strip().upper()
            queryset = Department.objects.filter(department_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.filter(is_archived=False).exists():
                raise serializers.ValidationError("Department code already exists.")
        return value

    def validate_parent_department(self, value):
        """Validate parent department"""
        if value:
            # Cannot set self as parent
            if self.instance and value.id == self.instance.id:
                raise serializers.ValidationError(
                    "Department cannot be its own parent."
                )
            # Parent must be in same plant (if both have plants)
            instance_plant = self.instance.plant if self.instance else None
            if instance_plant and value.plant and value.plant != instance_plant:
                raise serializers.ValidationError(
                    "Parent department must be in the same plant."
                )
            # Parent must not be archived
            if value.is_archived:
                raise serializers.ValidationError(
                    "Cannot assign archived department as parent."
                )
        return value

    def validate(self, attrs):
        """Additional validation"""
        # Cannot edit archived departments
        if self.instance and self.instance.is_archived:
            raise serializers.ValidationError("Cannot edit archived department.")

        # Check if can deactivate
        if attrs.get("status") == "Inactive" and self.instance:
            from common.services.department_service import can_deactivate_department

            can_deactivate, message = can_deactivate_department(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"status": message})

        # Validate parent department plant matches (if both have plants)
        plant = attrs.get("plant") or (self.instance.plant if self.instance else None)
        parent_department = attrs.get("parent_department")
        if (
            parent_department
            and plant
            and parent_department.plant
            and parent_department.plant != plant
        ):
            raise serializers.ValidationError(
                {"parent_department": "Parent department must be in the same plant."}
            )

        return attrs

    def update(self, instance, validated_data):
        """Ensure updated_at and updated_by are set on manual update."""
        validated_data.pop("updated_at", None)
        updated_by = validated_data.pop("updated_by", None)
        super().update(instance, validated_data)
        instance.updated_at = timezone.now()
        update_fields = ["updated_at"]
        if updated_by is not None:
            instance.updated_by = updated_by
            update_fields.append("updated_by")
        instance.save(update_fields=update_fields)
        return instance


class DepartmentDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Department dropdown API - active and non-archived only"""

    class Meta:
        model = Department
        fields = ["id", "department_code", "department_name"]


class ItemCategorySerializer(serializers.ModelSerializer):
    """Serializer for ItemCategory model"""

    created_by_info = UserQuickSerializer(source="created_by", read_only=True)
    updated_by_info = UserQuickSerializer(source="updated_by", read_only=True)

    class Meta:
        model = ItemCategory
        fields = [
            "id",
            "category_code",
            "category_name",
            "allowed_item_type",
            "description",
            "status",
            "is_archived",
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
            "is_archived",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {"category_code": {"validators": []}}

    def validate_category_code(self, value):
        """Case-insensitive unique validation for category_code"""
        if value:
            value = value.strip().upper()
            queryset = ItemCategory.objects.filter(category_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.filter(is_archived=False).exists():
                raise serializers.ValidationError("SubCategory code already exists.")
        return value

    def validate(self, attrs):
        """Additional validation"""
        # Cannot edit archived categories
        if self.instance and self.instance.is_archived:
            raise serializers.ValidationError("Cannot edit archived item category.")

        # Check if can deactivate
        if attrs.get("status") == False and self.instance:
            from common.services.item_category_service import (
                can_deactivate_item_category,
            )

            can_deactivate, message = can_deactivate_item_category(self.instance)
            if not can_deactivate:
                raise serializers.ValidationError({"status": message})

        return attrs


class ItemCategoryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Item Category dropdown API - active and non-archived only"""

    class Meta:
        model = ItemCategory
        fields = ["id", "category_code", "category_name", "allowed_item_type"]


class StoreTypeSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)

    class Meta:
        model = StoreType
        fields = [
            "id",
            "name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        """Validate name uniqueness (case-insensitive)"""
        if value:
            queryset = StoreType.objects.filter(name__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "A store type with this name already exists."
                )
        return value


class StoreTypeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for StoreType dropdown API"""

    class Meta:
        model = StoreType
        fields = ["id", "name"]


