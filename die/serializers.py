import math

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms import ValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.filters import SearchFilter

from bloster.serializers import BlosterMasterSortSerializer
from common.serializers import BaseModelSerializer
from customer.models import Customer
from customer.serializers import CustomerSerializer
from die.master_serializers import DiePressSerializers
from die.models import ConversionRate, Die, DieTool
from die.sort_serializers import (
    DieCategorySortSerializers,
    DieGroupSortSerializers,
    DieSizeSortSerializers,
    DieSortSerializers,
    DieSubCategorySortSerializers,
)
from product.models import Alloy, Temper

from .models import DieInformation, DieToolBrokenImage, SectionBallonDimensions

from decimal import Decimal, InvalidOperation


class DieSerializers(BaseModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), allow_null=True, required=False
    )

    class Meta(BaseModelSerializer.Meta):
        model = Die
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "die_number",
            "die_type",
            "dimension1",
            "dimension2",
            "dimension3",
            "dimension4",
            "description",
            "customer",
            "ownership_type",
            "cutting_dimensions",
            "min_wt_kg_p_mt",
            "wt_kg_p_mt",
            "max_wt_kg_p_mt",
            "die_group",
            "die_category",
            "die_sub_category",
            "die_type",
            "die_diagram",
            "die_detail_diagram",
            "customer_approved_diagram",
            "ccd_mm",
            "perimeter_outer",
            "area",
            "process_description",
            "autocad_drawing",
            "die_manufacturing",
            "die_sop",
            "remarks",
            "customer_reference_number",
            "front_end_process_loss_mm",
            "back_end_process_loss_mm",
            "stretching_head_loss_mm",
            "stretching_tail_loss_mm",
            "total_process_loss_mm",
            "total_process_loss_meter",
            "total_process_loss_kg",
        ]

    def validate_cutting_dimensions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("cutting_dimensions must be a list.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        instance = self.instance

        if request and request.method in ["PATCH", "PUT"] and instance:
            if "die_number" in attrs:
                new_die_number = attrs["die_number"]
                if new_die_number != instance.die_number:
                    if (
                        Die.objects.filter(die_number=new_die_number)
                        .exclude(id=instance.id)
                        .exists()
                    ):
                        raise ValidationError("Die number already exists.")
        else:
            if Die.objects.filter(die_number=attrs["die_number"]).exists():
                raise ValidationError("Die number already exists.")

        return attrs

    def handle_nan(self, value):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value

    def run_validation(self, data):
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        for field in [
            "dimension1",
            "dimension2",
            "dimension3",
            "dimension4",
            "min_wt_kg_p_mt",
            "wt_kg_p_mt",
            "max_wt_kg_p_mt",
            "total_running_ton",
        ]:
            if field in ret:
                ret[field] = self.handle_nan(ret[field])

        if "die_category" in ret:
            ret["die_category"] = DieCategorySortSerializers(instance.die_category).data

        if "die_sub_category" in ret:
            ret["die_sub_category"] = DieSubCategorySortSerializers(
                instance.die_sub_category
            ).data

        if "die_group" in ret:
            ret["die_group"] = DieGroupSortSerializers(instance.die_group).data

        if "customer" in ret:
            ret["customer"] = CustomerSerializer(instance.customer).data

        if "die_size" in ret:
            ret["die_size"] = DieSizeSortSerializers(instance.die_size).data

        ret["number_of_dietools"] = DieTool.objects.filter(die=instance.id).count()

        return ret


class SectionBallonDimensionsSerializer(BaseModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)

        for field in ["nominal_value", "min_value", "max_value"]:
            value = data.get(field)

            if value not in [None, ""]:
                try:
                    data[field] = f"{Decimal(str(value)):.2f}"
                except (InvalidOperation, ValueError):
                    pass

        return data
     
    class Meta(BaseModelSerializer.Meta):
        model = SectionBallonDimensions
        fields = "__all__"


class DieInformationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    class Meta:
        model = DieInformation
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "customer_name")


class DieWithBallonListSerializer(BaseModelSerializer):
    drawing_reference_no = serializers.CharField(read_only=True)
    die_group = serializers.CharField(source="die_group.name", read_only=True)
    die_category = serializers.CharField(source="die_category.name", read_only=True)
    die_sub_category = serializers.CharField(source="die_sub_category.name", read_only=True)
    number_of_dietools = serializers.IntegerField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Die
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "area",
            "die_number",
            "die_diagram",
            "description",
            "dimension1",
            "dimension2",
            "dimension3",
            "dimension4",
            "drawing_reference_no",
            "wt_kg_p_mt",
            "die_group",
            "die_type",
            "die_category",
            "number_of_dietools",
            "die_sub_category",
            "customer_reference_number",
            "ownership_type",
            "remarks"
        ]

class DieWithBallonSerializer(BaseModelSerializer):
    balloon_drawing_dimensions = SectionBallonDimensionsSerializer(
        source="ballon_drawing_dimensions", many=True, required=False
    )
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), allow_null=True, required=False
    )
    extrusion_die_info = DieInformationSerializer(many=True, required=False)

    class Meta(BaseModelSerializer.Meta):
        model = Die
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "die_number",
            "die_type",
            "dimension1",
            "dimension2",
            "dimension3",
            "dimension4",
            "customer",
            "ownership_type",
            "cutting_dimensions",
            "description",
            "min_wt_kg_p_mt",
            "wt_kg_p_mt",
            "max_wt_kg_p_mt",
            "die_group",
            "die_category",
            "die_sub_category",
            "die_diagram",
            "die_detail_diagram",
            "customer_approved_diagram",
            "autocad_drawing",
            "die_manufacturing",
            "die_sop",
            "remarks",
            "customer_reference_number",
            "ccd_mm",
            "perimeter_outer",
            "area",
            "process_description",
            "wt_kg_p_mt",
            "balloon_drawing_dimensions",
            "extrusion_die_info",
            "front_end_process_loss_mm",
            "back_end_process_loss_mm",
            "stretching_head_loss_mm",
            "stretching_tail_loss_mm",
            "total_process_loss_mm",
            "total_process_loss_meter",
            "total_process_loss_kg",
        ]

    def format_decimal(self, value):
        if value is None:
            return None

        try:
            value = Decimal(value)
            value = value.normalize()

            return format(value, 'f')
        except:
            return value

    def validate(self, attrs):
        request = self.context.get("request")
        instance = self.instance

        if request and request.method in ["PATCH", "PUT"] and instance:
            if "die_number" in attrs:
                new_die_number = attrs["die_number"]
                if new_die_number != instance.die_number:
                    if (
                        Die.objects.filter(die_number=new_die_number)
                        .exclude(id=instance.id)
                        .exists()
                    ):
                        raise ValidationError("Die number already exists.")
        else:
            if Die.objects.filter(die_number=attrs["die_number"]).exists():
                raise ValidationError("Die number already exists.")

        return attrs

    def handle_nan(self, value):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value

    def run_validation(self, data):
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        for field in [
            "dimension1",
            "dimension2",
            "dimension3",
            "dimension4",
            "min_wt_kg_p_mt",
            "wt_kg_p_mt",
            "max_wt_kg_p_mt",
        ]:
            if ret.get(field) is not None:
                ret[field] = self.handle_nan(ret[field])

        file_fields = [
            "die_diagram",
            "die_detail_diagram",
            "customer_approved_diagram",
            "autocad_drawing",
            "die_manufacturing",
            "die_sop",
        ]
        for field in file_fields:
            ret[field] = getattr(instance, field)

        ret["die_group"] = (
            DieGroupSortSerializers(instance.die_group).data
            if instance.die_group
            else None
        )
        ret["die_category"] = (
            DieCategorySortSerializers(instance.die_category).data
            if instance.die_category
            else None
        )
        ret["customer"] = (
            CustomerSerializer(instance.customer).data if instance.customer else None
        )
        ret["die_sub_category"] = (
            DieSubCategorySortSerializers(instance.die_sub_category).data
            if instance.die_sub_category
            else None
        )

        ret["number_of_dietools"] = DieTool.objects.filter(die=instance).count()

        zero_values_fields = [
            "total_process_loss_mm",
            "total_process_loss_meter",
            "total_process_loss_kg",
        ]

        for field in zero_values_fields:
            value = ret.get(field)

            if value is not None:
                try:
                    if float(value) == 0.0:
                        ret[field] = None
                except (ValueError, TypeError):
                    pass

        decimal_fields = [
            "perimeter_outer", "area",
            "front_end_process_loss_mm", "back_end_process_loss_mm",
            "stretching_head_loss_mm", "stretching_tail_loss_mm",
            "total_process_loss_mm", "total_process_loss_meter",
            "total_process_loss_kg",
        ]

        for field in decimal_fields:
            if field in ret:
                ret[field] = self.format_decimal(ret[field])
        return ret

    @transaction.atomic
    def create(self, validated_data):
        ballon_data = validated_data.pop("ballon_drawing_dimensions", [])
        extrusion_data = validated_data.pop("extrusion_die_info", [])
        validated_data["created_by"] = self.context["request"].user

        die_instance = Die.objects.create(**validated_data)

        for ballon_item in ballon_data:
            ballon_item["section"] = die_instance
            ballon_item["created_by"] = self.context["request"].user
            SectionBallonDimensions.objects.create(**ballon_item)

        for extrusion_item in extrusion_data:
            extrusion_item["section"] = die_instance
            DieInformation.objects.create(**extrusion_item)

        return die_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        ballon_data = validated_data.pop("ballon_drawing_dimensions", None)
        extrusion_data = validated_data.pop("extrusion_die_info", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context["request"].user
        instance.updated_at = timezone.now()
        instance.save()

        if ballon_data is not None:
            existing_ids = set(
                instance.ballon_drawing_dimensions.filter(deleted=False).values_list(
                    "id", flat=True
                )
            )
            incoming_ids = set()

            for item in ballon_data:
                item_id = item.get("id")
                if item_id:
                    incoming_ids.add(item_id)
                    try:
                        ballon_obj = SectionBallonDimensions.objects.get(
                            id=item_id, section=instance, deleted=False
                        )
                        for attr, value in item.items():
                            if attr != "id":
                                setattr(ballon_obj, attr, value)
                        ballon_obj.updated_by = self.context["request"].user
                        ballon_obj.save()
                    except SectionBallonDimensions.DoesNotExist:
                        pass
                else:
                    new_ballon = SectionBallonDimensions.objects.create(
                        section=instance,
                        created_by=self.context["request"].user,
                        **item,
                    )
                    incoming_ids.add(new_ballon.id)

            to_delete = existing_ids - incoming_ids
            if to_delete:
                SectionBallonDimensions.objects.filter(id__in=to_delete).update(
                    deleted=True,
                    deleted_by=self.context["request"].user,
                    deleted_at=timezone.now(),
                )

        if extrusion_data is not None:
            existing_ids = set(
                instance.extrusion_die_info.all().values_list("id", flat=True)
            )
            incoming_ids = set()

            for item in extrusion_data:
                print("ITEM =", item)
                print("ITEM ID =", item.get("id"))
                item_id = item.get("id")

                if item_id:
                    incoming_ids.add(item_id)
                    try:
                        extrusion_obj = DieInformation.objects.get(
                            id=item_id, section=instance,
                        )
                        for attr, value in item.items():
                            if attr != "id":
                                setattr(extrusion_obj, attr, value)

                        extrusion_obj.save()

                    except DieInformation.DoesNotExist:
                        pass

                else:
                    new_extrusion = DieInformation.objects.create(
                        section=instance,
                        **item,
                    )
                    incoming_ids.add(new_extrusion.id)

            to_delete = existing_ids - incoming_ids
            if to_delete:
                DieInformation.objects.filter(id__in=to_delete).delete()

        return instance


class DieBrokenImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DieToolBrokenImage
        fields = ["id", "image"]


class DieToolSerializers(BaseModelSerializer):
    die_count = serializers.SerializerMethodField()
    broken_part = serializers.ListField(
        child=serializers.ChoiceField(choices=DieTool.BROKEN_PART_CHOICES),
        required=False, allow_empty=True
    )

    die_broken_images = DieBrokenImageSerializer(many=True, read_only=True, allow_null=True, required=False)

    vendor = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.filter(company_type="vendor"),
        allow_null=True,
        required=False,
    )
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        allow_null=True,
        required=False,
    )
    scrap_approved_by_detail = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = DieTool
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "die",
            "actual_kg",
            "drawing_kg",
            "weight_diff_kg",
            "tool_number",
            "die_size",
            "die_broken_images",
            "die_cavity",
            "vendor",
            "customer",
            "extrusion_ratio",
            "developer_ref_no",
            "eligible_for_press",
            "broken_part",
            "damage_severity",
            "die_broken_note",
            "first_bloster",
            "second_bloster",
            "third_bloster",
            "material_grade",
            "received_date",
            "order_date",
            "total_running_kg",
            "max_die_life",
            "feeder_number",
            "remaining_life",
            "purchase_price",
            "tool_status",
            "tool_status_inactive",
            "tool_status_reason",
            "ownership",
            "is_active",
            "remarks",
            "drawing_no",
            "die_oblique_number",
            "rac_no",
            "row_no",
            "column_no",
            "die_location",
            "die_option",
            "diameter",
            "backer_number",
            "thickness",
            "scrap_date",
            "scrap_weight",
            "scrap_approved_by",
            "scrap_approved_by_detail",
            "die_count",
        ]

    def get_scrap_approved_by_detail(self, obj):
        if obj.scrap_approved_by:
            return {
                "id": obj.scrap_approved_by.id,
                "first_name": obj.scrap_approved_by.first_name,
                "last_name": obj.scrap_approved_by.last_name,
            }
        return None

    def get_die_count(self, obj):
        return obj.dies.count() if hasattr(obj, "dies") and obj.dies is not None else 0

    def validate(self, attrs):
        if attrs.get("run_under_deviation") == "inactive":
            if not attrs.get("run_under_deviation_inactive") in [
                "die_broken",
                "die_absolute",
                "die_shift",
                "other",
            ]:
                raise serializers.ValidationError(
                    {"run_under_deviation_inactive": "Invalid Selection"}
                )
            if attrs.get("run_under_deviation_inactive") == "other":
                if not attrs.get("run_under_deviation_reason"):
                    raise serializers.ValidationError(
                        {"run_under_deviation_reason": "Reason is required"}
                    )
            else:
                attrs["run_under_deviation_reason"] = None
        elif attrs.get("run_under_deviation") == "active":
            if attrs.get("run_under_deviation_inactive") or attrs.get(
                "run_under_deviation_reason"
            ):
                raise serializers.ValidationError(
                    {"run_under_deviation": "Invalid Selection"}
                )

        return attrs

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["die"] = DieSortSerializers(instance.die).data
        response["die_size"] = (
            DieSizeSortSerializers(instance.die_size).data
            if instance.die_size
            else None
        )
        response["vendor"] = (
            CustomerSerializer(instance.vendor).data if instance.vendor else None
        )
        response["customer"] = (
            CustomerSerializer(instance.customer).data if instance.customer else None
        )
        response["first_bloster"] = (
            BlosterMasterSortSerializer(instance.first_bloster.all(), many=True).data
            if instance.first_bloster.exists()
            else []
        )
        response["second_bloster"] = (
            BlosterMasterSortSerializer(instance.second_bloster.all(), many=True).data
            if instance.second_bloster.exists()
            else []
        )
        response["third_bloster"] = (
            BlosterMasterSortSerializer(instance.third_bloster.all(), many=True).data
            if instance.third_bloster.exists()
            else []
        )
        response["eligible_for_press"] = (
            DiePressSerializers(instance.eligible_for_press).data
            if instance.eligible_for_press
            else None
        )

        drawing = instance.drawing_kg or Decimal("0")
        actual = instance.actual_kg or Decimal("0")

        if drawing > 0 and actual > 0:
            kg_diff = actual - drawing
            percent = (kg_diff / drawing) * Decimal("100")

            response["weight_diff_kg"] = f"{kg_diff:+.3f}"
            response["weight_diff_per"] = f"{percent:+.2f}%"
        else:
            response["weight_diff_kg"] = ""
            response["weight_diff_per"] = ""

        return response


class QuickDieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Die
        fields = ["id", "die_number", "die_type", "wt_kg_p_mt"]

    def validate_die_number(self, value):
        qs = Die.objects.filter(die_number=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("Die number already exists.")
        return value


class DieListField(serializers.Field):
    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError("Expected a list of die IDs.")

        if not all(isinstance(i, int) for i in data):
            raise serializers.ValidationError("All die IDs must be integers.")

        invalid_die_ids = [
            die_id for die_id in data if not Die.objects.filter(id=die_id).exists()
        ]
        if invalid_die_ids:
            raise serializers.ValidationError(
                f"Invalid die ID(s): {', '.join(map(str, invalid_die_ids))}"
            )

        return data

    def to_representation(self, value):
        if isinstance(value, list):
            return value
        return []


class ConversionRateEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    die = serializers.PrimaryKeyRelatedField(queryset=Die.objects.all())
    alloy = serializers.PrimaryKeyRelatedField(queryset=Alloy.objects.all())
    temper = serializers.PrimaryKeyRelatedField(queryset=Temper.objects.all())
    conversion = serializers.DecimalField(max_digits=10, decimal_places=2)
    remarks = serializers.CharField(allow_blank=True, required=False)

    def update(self, instance, validated_data):
        instance.customer = validated_data.get("customer", instance.customer)
        instance.die = validated_data.get("die", instance.die)
        instance.alloy = validated_data.get("alloy", instance.alloy)
        instance.temper = validated_data.get("temper", instance.temper)
        instance.conversion = validated_data.get("conversion", instance.conversion)
        instance.remarks = validated_data.get("remarks", instance.remarks)

        updated_by = self.context.get("updated_by")
        if updated_by:
            instance.updated_by = updated_by

        instance.save()
        return instance


class ConversionRateReadSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    die = serializers.SerializerMethodField()
    alloy = serializers.SerializerMethodField()
    temper = serializers.SerializerMethodField()
    die_diagram = serializers.SerializerMethodField()

    customer_id = serializers.IntegerField(source="customer.id", read_only=True)
    die_id = serializers.IntegerField(source="die.id", read_only=True)
    alloy_id = serializers.IntegerField(source="alloy.id", read_only=True)
    temper_id = serializers.IntegerField(source="temper.id", read_only=True)

    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    class Meta:
        model = ConversionRate
        fields = [
            "id",
            "customer_id",
            "customer",
            "die_id",
            "die",
            "die_diagram",
            "alloy_id",
            "alloy",
            "temper_id",
            "temper",
            "conversion",
            "remarks",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_created_by(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_updated_by(self, obj):
        return obj.updated_by.get_full_name() if obj.updated_by else None

    def get_die(self, obj):
        return f"{obj.die.die_number}" if obj.die else None

    def get_die_diagram(self, obj):
        return obj.die.die_diagram if obj.die and obj.die else None

    def get_customer(self, obj):
        return f"{obj.customer.customer_name}" if obj.customer else None

    def get_alloy(self, obj):
        return (
            f"{obj.alloy.alloy_code} - "
            f"{obj.alloy.standard_name}"
            f"{f' - {obj.alloy.color_code}' if obj.alloy.color_code else ''}"
            if obj.alloy
            else None
        )

    def get_temper(self, obj):
        return f"{obj.temper.name}" if obj.temper else None


class CustomDuplicateException(APIException):
    status_code = 400

    def __init__(self, message):
        self.detail = {"status": 400, "message": message}


class CustomDieSearchFilter(SearchFilter):
    def get_search_terms(self, request):
        return request.query_params.get(self.search_param, "").split()

    def construct_search(self, field_name):
        if field_name == "die":
            return None
        return super().construct_search(field_name)

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)

        orm_lookups = self.get_search_fields(view, request)
        base_q = Q()

        for term in search_terms:
            q = Q()

            for field in orm_lookups:
                if field == "die":
                    q |= (
                        Q(die__icontains=f",{term},")
                        | Q(die__startswith=f"{term},")
                        | Q(die__endswith=f",{term}")
                        | Q(die=term)
                    )
                else:
                    q |= Q(**{f"{field}__icontains": term})

            base_q &= q

        return queryset.filter(base_q)
