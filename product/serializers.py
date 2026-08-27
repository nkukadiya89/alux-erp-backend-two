from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from common.master_serializers import UOMDropdownSerializer, YieldUnitSerializers
from common.serializers import (
    BaseModelSerializer,
    ItemCategoryDropdownSerializer,
    SectionQuickSerializer,
)
from product.models import Alloy, Item, Temper, StandardMaster
from user.serializers import UserQuickSerializer
from decimal import Decimal

def format_decimal(value):
    if value is None:
        return value

    try:
        value = Decimal(str(value))
    except Exception:
        return value

    normalized = value.normalize()

    if normalized == normalized.to_integral():
        return int(normalized)
    return float(normalized)

class StandardMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardMaster
        fields = ["id", "name"]

class TemperSerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)

    _DECIMAL_FIELDS = [
        "elongation_50mm_min",
        "elongation_min",
        "hardness",
        "tensile_min",
        "tensile_max",
        "yield_min",
        "yield_max",
        "electrical_conductivity_min",
        "electrical_conductivity_max",
    ]

    class Meta:
        model = Temper
        fields = [
            "id",
            "description",
            "section_type",
            "area",
            "alloy",
            "standard",
            "dimention_unit",
            "elongation_50mm_min",
            "elongation_min",
            "hardness",
            "section_thickness_over",
            "section_thickness_upto",
            "tensile_min",
            "tensile_max",
            "yield_min",
            "yield_max",
            "yield_unit",
            "electrical_conductivity_min",
            "electrical_conductivity_max",
            "temper_code_old",
            "temper_code_new",
            "heat_treatment",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = [
            "deleted",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        extra_kwargs = {
            "section_type": {"required": False, "allow_null": True},
            "dimention_unit": {"required": False, "allow_null": True},
            "yield_unit": {"required": False, "allow_null": True},
            "alloy": {"required": False, "allow_null": True},
        }
        validators = []

    def validate(self, data):
        temper_code_new = data.get("temper_code_new")
        section_type = (
            data.get("section_type", None)
            if "section_type" in data
            else (self.instance.section_type if self.instance else None)
        )
        alloy = (
            data.get("alloy", None)
            if "alloy" in data
            else (self.instance.alloy if self.instance else None)
        )

        filter_kwargs = {
            "description": data.get("description"),
            "temper_code_new": temper_code_new,
            "alloy": alloy,
            "deleted": False,
        }

        if section_type is not None:
            filter_kwargs["section_type"] = section_type
        else:
            filter_kwargs["section_type__isnull"] = True
        queryset = Temper.objects.filter(**filter_kwargs)

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError(
                "Temper with this combination already exists."
            )

        tensile_min = data.get("tensile_min")
        tensile_max = data.get("tensile_max")
        if tensile_min is not None and tensile_max is not None:
            if tensile_min > tensile_max:
                raise serializers.ValidationError(
                    "tensile_min cannot be greater than tensile_max"
                )

        yield_min = data.get("yield_min")
        yield_max = data.get("yield_max")
        if yield_min is not None and yield_max is not None:
            if yield_min > yield_max:
                raise serializers.ValidationError(
                    "yield_min cannot be greater than yield_max"
                )

        electrical_conductivity_min = data.get("electrical_conductivity_min")
        electrical_conductivity_max = data.get("electrical_conductivity_max")
        if (
            electrical_conductivity_min is not None
            and electrical_conductivity_max is not None
        ):
            if electrical_conductivity_min > electrical_conductivity_max:
                raise serializers.ValidationError(
                    "electrical_conductivity_min cannot be greater than electrical_conductivity_max"
                )
        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if "section_type" in ret and instance.section_type:
            ret["section_type"] = SectionQuickSerializer(instance.section_type).data
        elif "section_type" in ret and not instance.section_type:
            ret["section_type"] = None

        if "standard" in ret and instance.standard:
            ret["standard"] = StandardMasterSerializer(instance.standard).data
        elif "standard" in ret and not instance.standard:
            ret["standard"] = None


        if "alloy" in ret and instance.alloy:
            ret["alloy"] = AlloyDropdownSerializer(instance.alloy).data
        elif "alloy" in ret and not instance.alloy:
            ret["alloy"] = None

        if "dimention_unit" in ret and instance.dimention_unit:
            ret["dimention_unit"] = UOMDropdownSerializer(instance.dimention_unit).data
        elif "dimention_unit" in ret and not instance.dimention_unit:
            ret["dimention_unit"] = None

        if "yield_unit" in ret and instance.yield_unit:
            ret["yield_unit"] = YieldUnitSerializers(instance.yield_unit).data
        elif "yield_unit" in ret and not instance.yield_unit:
            ret["yield_unit"] = None
        

        
        decimal_fields = [
            "elongation_50mm_min",
            "elongation_min",
            "hardness",
            "tensile_min",
            "tensile_max",
            "yield_min",
            "yield_max",
            "electrical_conductivity_min",
            "electrical_conductivity_max",
        ]

        for field in decimal_fields:
            value = ret.get(field)
            if value is not None:
                ret[field] = format_decimal(value)

        return ret

class TemperDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Temper dropdown API - active and non-archived only"""

    class Meta:
        model = Temper
        fields = ["id", "description"]


class AlloyDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Alloy dropdown API - active and non-archived only"""

    class Meta:
        model = Alloy
        fields = ["id", "alloy_code", "color_code"]


class AlloySerializers(BaseModelSerializer):
    standard = serializers.PrimaryKeyRelatedField(
        queryset=StandardMaster.objects.all(), allow_null=True, required=False
    )
    class Meta(BaseModelSerializer.Meta):
        model = Alloy
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "alloy_code",
            "color_code",
            "standard",
            "si_min",
            "si_max",
            "mg_min",
            "mg_max",
            "fe_min",
            "fe_max",
            "mn_min",
            "mn_max",
            "cu_min",
            "cu_max",
            "zn_min",
            "zn_max",
            "cr_min",
            "cr_max",
            "ti_min",
            "ti_max",
            "bi_min",
            "bi_max",
            "pb_min",
            "pb_max",
            "sn_min",
            "sn_max",
            "al_min",
            "al_max",
            "others_each_min",
            "others_each_max",
            "others_total_min",
            "others_total_max",
            "remark",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        decimal_fields = [
            "si_min",
            "si_max",
            "mg_min",
            "mg_max",
            "fe_min",
            "fe_max",
            "mn_min",
            "mn_max",
            "cu_min",
            "cu_max",
            "zn_min",
            "zn_max",
            "cr_min",
            "cr_max",
            "ti_min",
            "ti_max",
            "bi_min",
            "bi_max",
            "pb_min",
            "pb_max",
            "sn_min",
            "sn_max",
            "others_each_min",
            "others_each_max",
            "others_total_min",
            "others_total_max",
            "al_min",
            "al_max",
        ]

        if "standard" in ret and instance.standard:
            ret["standard"] = StandardMasterSerializer(instance.standard).data
        elif "standard" in ret and not instance.standard:
            ret["standard"] = None

        for f in decimal_fields:
            v = ret.get(f)
            if v is None or v == "":
                continue
            s = str(v)
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            ret[f] = s

        return ret

    def validate(self, data):
        for field in ["alloy_code", "color_code"]:
            if data.get(field) == "":
                data[field] = None

        alloy_code = data.get(
            "alloy_code", self.instance.alloy_code if self.instance else None
        )
        if alloy_code:
            qs = Alloy.objects.filter(alloy_code=alloy_code, deleted=False)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError(
                    {"alloy_code": "Alloy with this alloy code already exists."}
                )

        decimal_fields = [
            "si_min",
            "si_max",
            "mg_min",
            "mg_max",
            "fe_min",
            "fe_max",
            "mn_min",
            "mn_max",
            "cu_min",
            "cu_max",
            "zn_min",
            "zn_max",
            "cr_min",
            "cr_max",
            "ti_min",
            "ti_max",
            "bi_min",
            "bi_max",
            "pb_min",
            "pb_max",
            "sn_min",
            "sn_max",
            "others_each_min",
            "others_each_max",
            "others_total_min",
            "others_total_max",
        ]

        for field in decimal_fields:
            if field not in data:
                continue
            raw_val = data.get(field)
            if raw_val is None or raw_val == "":
                continue

            try:
                dec_val = (
                    raw_val
                    if isinstance(raw_val, Decimal)
                    else Decimal(str(raw_val).strip())
                )
            except (InvalidOperation, ValueError):
                raise serializers.ValidationError({field: f"{field} must be a number"})

            frac_digits = max(-dec_val.as_tuple().exponent, 0)
            if frac_digits > 3:
                raise serializers.ValidationError(
                    {field: f"{field} must have at most 3 decimal places"}
                )

            t = dec_val.as_tuple()
            total_digits = len(t.digits)
            exp = t.exponent
            if exp > 0:
                int_digits = total_digits + exp
            else:
                int_digits = max(total_digits - frac_digits, 0)
            if int_digits > 3:
                raise serializers.ValidationError(
                    {
                        field: f"{field} must have at most 3 digits before the decimal point"
                    }
                )

            if dec_val > Decimal("100"):
                raise serializers.ValidationError(
                    {field: f"{field} must be less than or equal to 100"}
                )

        percent_pairs = [
            ("si_min", "si_max"),
            ("mg_min", "mg_max"),
            ("fe_min", "fe_max"),
            ("mn_min", "mn_max"),
            ("cu_min", "cu_max"),
            ("zn_min", "zn_max"),
            ("cr_min", "cr_max"),
            ("ti_min", "ti_max"),
            ("bi_min", "bi_max"),
            ("pb_min", "pb_max"),
            ("sn_min", "sn_max"),
            ("others_each_min", "others_each_max"),
            ("others_total_min", "others_total_max"),
        ]

        for min_f, max_f in percent_pairs:
            min_val = data.get(min_f)
            max_val = data.get(max_f)
            if min_val is not None and max_val is not None:
                if min_val > max_val:
                    raise serializers.ValidationError(
                        {min_f: f"{min_f} cannot be greater than {max_f}"}
                    )

        source = {}
        if self.instance:
            for f in Alloy.AL_COMPONENT_MIN_FIELDS + Alloy.AL_COMPONENT_MAX_FIELDS:
                source[f] = getattr(self.instance, f, None)
        source.update(
            {
                k: v
                for k, v in data.items()
                if k in (Alloy.AL_COMPONENT_MIN_FIELDS + Alloy.AL_COMPONENT_MAX_FIELDS)
            }
        )

        def _has_any(fields) -> bool:
            for f in fields:
                v = source.get(f)
                if v is None:
                    continue
                if isinstance(v, str) and v.strip() == "":
                    continue
                return True
            return False

        has_min_values = _has_any(Alloy.AL_COMPONENT_MIN_FIELDS)
        has_max_values = _has_any(Alloy.AL_COMPONENT_MAX_FIELDS)

        if has_min_values:
            sum_min = sum(
                (Decimal(str(v)) if v is not None and v != "" else Decimal("0"))
                for v in [source.get(f) for f in Alloy.AL_COMPONENT_MIN_FIELDS]
            )
            if sum_min > Decimal("100"):
                raise serializers.ValidationError(
                    {"__all__": "Sum of all Min fields cannot exceed 100."}
                )

        if has_max_values:
            sum_max = sum(
                (Decimal(str(v)) if v is not None and v != "" else Decimal("0"))
                for v in [source.get(f) for f in Alloy.AL_COMPONENT_MAX_FIELDS]
            )
            if sum_max > Decimal("100"):
                raise serializers.ValidationError(
                    {"__all__": "Sum of all Max fields cannot exceed 100."}
                )

        al_min, al_max = Alloy.calculate_al_min_max(source)
        if al_min is None:
            data["al_min"] = None
        if al_max is None:
            data["al_max"] = None

        if al_min is not None and al_min < 0:
            raise serializers.ValidationError(
                {"al_min": "Sum of Min fields exceeds 100. Cannot calculate Al Min."}
            )
        if al_min is not None:
            data["al_min"] = al_min
        if al_max is not None:
            data["al_max"] = al_max

        return data


class AlloyListSerializers(serializers.ModelSerializer):
    standard = serializers.CharField(source="standard.name", read_only=True)
    created_by = serializers.CharField(source="created_by.first_name", read_only=True)
    updated_by = serializers.CharField(source="updated_by.first_name", read_only=True)
    deleted_by = serializers.CharField(source="deleted_by.first_name", read_only=True)
    class Meta:
        model = Alloy
        fields = [
            "id",
            "alloy_code",
            "color_code",
            "standard",
            "si_min",
            "si_max",
            "mg_min",
            "mg_max",
            "fe_min",
            "fe_max",
            "mn_min",
            "mn_max",
            "cu_min",
            "cu_max",
            "zn_min",
            "zn_max",
            "cr_min",
            "cr_max",
            "ti_min",
            "ti_max",
            "bi_min",
            "bi_max",
            "pb_min",
            "pb_max",
            "sn_min",
            "sn_max",
            "al_min",
            "al_max",
            "others_each_min",
            "others_each_max",
            "others_total_min",
            "others_total_max",
            "remark",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

class ItemTypeQuickSerializer(serializers.ModelSerializer):
    """Quick serializer for ItemType"""

    class Meta:
        from product.models import ItemType

        model = ItemType
        fields = ["id", "name"]


class ValuationMethodQuickSerializer(serializers.ModelSerializer):
    """Quick serializer for ValuationMethod"""

    class Meta:
        from product.models import ValuationMethod

        model = ValuationMethod
        fields = ["id", "name"]


class MaterialCenterQuickSerializer(serializers.ModelSerializer):
    """Quick serializer for MaterialCenter"""

    class Meta:
        from product.models import MaterialCenter

        model = MaterialCenter
        fields = ["id", "name"]


class ItemSerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    category_info = ItemCategoryDropdownSerializer(source="category", read_only=True)
    uom_info = UOMDropdownSerializer(source="uom", read_only=True)
    item_type_info = ItemTypeQuickSerializer(source="item_type", read_only=True)
    valuation_method_info = ValuationMethodQuickSerializer(
        source="valuation_method", read_only=True
    )
    material_center_info = MaterialCenterQuickSerializer(
        source="material_center", read_only=True
    )

    class Meta:
        model = Item
        fields = [
            "id",
            "item_code",
            "item_name",
            "item_type",
            "item_type_info",
            "category",
            "category_info",
            "uom",
            "uom_info",
            "alloy_code",
            "heat_tracking",
            "reorder_level",
            "status",
            "hsn_code",
            "gst_rate",
            "base_unit",
            "net_weight",
            "purchase_rate",
            "sale_rate",
            "valuation_method",
            "valuation_method_info",
            "minimum_stock",
            "maximum_stock",
            "reorder_qty",
            "making_time_minutes",
            "lead_time_days",
            "bom_required",
            "material_center",
            "material_center_info",
            "batch_managed",
            "grn_required",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
            "category_info",
            "uom_info",
            "item_type_info",
            "valuation_method_info",
            "material_center_info",
        ]

    def validate_item_code(self, value):
        """Case-insensitive unique validation for item_code"""
        if value:
            value = value.strip().upper()
            queryset = Item.objects.filter(item_code__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.filter(deleted=False).exists():
                raise serializers.ValidationError("Item code already exists.")
        return value

    def validate_item_type(self, value):
        """Validate item_type ForeignKey"""
        if value:
            from product.models import ItemType

            if not ItemType.objects.filter(id=value.id).exists():
                raise serializers.ValidationError("Invalid item type.")
        return value

    def to_representation(self, instance):
        """Ensure UUID and ForeignKey fields are properly serialized"""
        ret = super().to_representation(instance)

        if "id" in ret:
            ret["id"] = str(ret["id"]) if ret["id"] else None
        if "uom" in ret:
            ret["uom"] = str(ret["uom"]) if ret["uom"] else None
        if "category" in ret:
            ret["category"] = str(ret["category"]) if ret["category"] else None
        if "item_type" in ret and ret["item_type"]:
            ret["item_type"] = (
                ret["item_type"]
                if isinstance(ret["item_type"], int)
                else int(ret["item_type"])
            )
        if "valuation_method" in ret and ret["valuation_method"]:
            ret["valuation_method"] = (
                ret["valuation_method"]
                if isinstance(ret["valuation_method"], int)
                else int(ret["valuation_method"])
            )
        if "material_center" in ret and ret["material_center"]:
            ret["material_center"] = (
                ret["material_center"]
                if isinstance(ret["material_center"], int)
                else int(ret["material_center"])
            )

        return ret

    def validate(self, attrs):
        item_type = attrs.get("item_type") or (
            self.instance.item_type if self.instance else None
        )
        heat_tracking = attrs.get("heat_tracking")

        if (
            item_type
            and hasattr(item_type, "name")
            and item_type.name == "RAW"
            and heat_tracking is False
        ):
            raise serializers.ValidationError(
                {"heat_tracking": "Heat tracking must be TRUE for RAW materials."}
            )

        category = attrs.get("category") or (
            self.instance.category if self.instance else None
        )
        if category:
            from common.models import ItemCategory

            if category.is_archived:
                raise serializers.ValidationError(
                    {"category": "Cannot assign archived category."}
                )
            if not category.status:
                raise serializers.ValidationError(
                    {"category": "Cannot assign inactive category."}
                )

        uom = attrs.get("uom") or (self.instance.uom if self.instance else None)
        if uom:
            from common.models import UOM

            if uom.deleted:
                raise serializers.ValidationError({"uom": "Cannot assign deleted UOM."})
            if not uom.is_active:
                raise serializers.ValidationError(
                    {"uom": "Cannot assign inactive UOM."}
                )

        return attrs

    def create(self, validated_data):
        """Create item - never set updated_at/updated_by on create (BaseModel leaves them null)."""
        validated_data.pop("updated_at", None)
        validated_data.pop("updated_by", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update item - updated_at/updated_by set by BaseModel.save() when user is passed."""
        validated_data.pop("updated_at", None)
        updated_by = validated_data.pop("updated_by", None)
        super().update(instance, validated_data)
        if updated_by is not None:
            instance.save(user=updated_by)
        return instance


class ItemDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Item dropdown API - active and non-deleted only"""

    class Meta:
        model = Item
        fields = ["id", "item_code", "item_name"]

    class Meta:
        model = Item
        fields = ["id", "item_code", "item_name"]
