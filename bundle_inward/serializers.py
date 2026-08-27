import math
from decimal import ROUND_HALF_UP, Decimal
from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from bundle_inward.models import BundleInward, ExcessStock
from common.serializers import (
    BaseModelSerializer,
    JobWorkSerializer,
    PackingModeSerializer,
)
from die.sort_serializers import DieSortSerializers
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from shift.models import ShiftMaster
from utils.generate_number import BundleNumberGenerator
from workorder.models import WorkOrderDetail
from workorder.serializers import WorkOrderDetailSerializers, WorkOrderSerializers


class BundleInwardSerializer(BaseModelSerializer):
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    avg_weight = serializers.SerializerMethodField()
    customer_name = serializers.CharField(
        source="workorder.bill_to.customer_name", read_only=True
    )
    die_number = serializers.CharField(
        source="workorder_detail.die_profile.die_number", read_only=True
    )
    die_description = serializers.CharField(
        source="workorder_detail.die_profile.description", read_only=True
    )
    surface_finish = JobWorkSerializer(
        source="workorder_detail.surface_finish", many=True, read_only=True
    )
    packing_mode = PackingModeSerializer(
        source="workorder.packing_mode", many=True, read_only=True
    )
    length = serializers.CharField(source="workorder_detail.length", read_only=True)
    alloy = AlloySortSerializers(source="workorder_detail.alloy", read_only=True)
    temper = TemperSortSerializers(source="workorder_detail.temper", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = BundleInward
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "workorder",
            "customer_name",
            "workorder_detail",
            "die_number",
            "die_description",
            "bundle_no",
            "length",
            "pieces",
            "weight",
            "avg_weight",
            "gross_weight",
            "packing_date",
            "dispatch_date",
            "hardness",
            "shift",
            "shift_details",
            "remarks",
            "status",
            "packing_mode",
            "surface_finish",
            "alloy",
            "temper",
        ]

    def get_shift_details(self, obj):
        if obj.shift_name_snapshot:
            return {
                "id": obj.shift.id if obj.shift else None,
                "name": obj.shift_name_snapshot,
                "start_time": obj.shift_start_snapshot,
                "end_time": obj.shift_end_snapshot,
            }
        return None

    def get_avg_weight(self, data):
        try:
            workorder_detail = data.workorder_detail
            if workorder_detail and workorder_detail.die_profile:
                length = workorder_detail.length or 0
                wt_kg_p_mt = workorder_detail.die_profile.wt_kg_p_mt or 0
                avg_weight = (length * wt_kg_p_mt) / 1000
                return round(avg_weight, 3)
        except Exception as e:
            return 0
        return 0

    def validate(self, attrs):
        DECIMAL_PRECISION = Decimal("0.001")
        workorder_detail_id = attrs.get("workorder_detail")
        pieces = attrs.get("pieces")
        weight = attrs.get("weight")

        if workorder_detail_id is not None:
            try:
                workorder_detail = WorkOrderDetail.objects.get(
                    id=workorder_detail_id.id
                )

                total_ordered_pieces = workorder_detail.pieces
                workorder_detail.net_weight
                tolerance = workorder_detail.workorder.tolerance
                die_over_weight = workorder_detail.die_over_weight

                percent = 0
                if tolerance:
                    percent_str = (
                        tolerance.replace("+-", "").replace("+", "").replace("%", "")
                    )
                    if percent_str.isdigit():
                        percent = int(percent_str)

                extra_percent = 0
                if die_over_weight:
                    extra_percent = 10
                    percent += extra_percent

                weight_per_piece = (
                    Decimal(workorder_detail.die_profile.wt_kg_p_mt)
                    * Decimal(workorder_detail.length)
                    / Decimal(1000)
                ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

                tolerance_percent = Decimal("10")
                tolerance_weight_per_piece = (
                    weight_per_piece * tolerance_percent / Decimal(100)
                ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

                normal_range_weight_per_piece = (
                    weight_per_piece + tolerance_weight_per_piece
                ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

                allowed_max_weight = (
                    normal_range_weight_per_piece * Decimal(pieces)
                ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

                expected_weight = (weight_per_piece * Decimal(pieces)).quantize(
                    DECIMAL_PRECISION, rounding=ROUND_HALF_UP
                )

                proportional_tolerance_percent = (
                    Decimal(pieces) / Decimal(total_ordered_pieces)
                ) * Decimal(percent)

                max_allowed_weight = (
                    expected_weight
                    + (expected_weight * proportional_tolerance_percent / Decimal(100))
                ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

                payload_weight = Decimal(str(weight)).quantize(
                    DECIMAL_PRECISION, rounding=ROUND_HALF_UP
                )

                existing_bundles = BundleInward.objects.filter(
                    workorder_detail=workorder_detail
                )
                total_existing_pieces = (
                    existing_bundles.aggregate(Sum("pieces"))["pieces__sum"] or 0
                )

                remaining_pieces = (
                    total_ordered_pieces
                    + math.ceil(total_ordered_pieces * percent / 100)
                    - total_existing_pieces
                )

                if pieces > remaining_pieces:
                    raise serializers.ValidationError(
                        f"Cannot create a bundle with {pieces} pieces. "
                        f"As per tolerance {tolerance or '0%'}, Max allowed pieces remaining: {int(remaining_pieces)}."
                    )

                if die_over_weight:
                    base_per_piece = weight_per_piece
                    min_per_piece = base_per_piece + (
                        base_per_piece * Decimal(percent - extra_percent) / Decimal(100)
                    )
                    max_per_piece = base_per_piece + (
                        base_per_piece * Decimal(percent) / Decimal(100)
                    )

                    min_total_weight = (min_per_piece * Decimal(pieces)).quantize(
                        DECIMAL_PRECISION, rounding=ROUND_HALF_UP
                    )

                    base_total_weight = (weight_per_piece * Decimal(pieces)).quantize(
                        DECIMAL_PRECISION, rounding=ROUND_HALF_UP
                    )

                    max_total_weight = (
                        base_total_weight * (Decimal(100 + percent) / Decimal(100))
                    ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

                    if not (base_total_weight <= payload_weight <= max_total_weight):
                        raise serializers.ValidationError(
                            f"Bundle weight is out of range. For {pieces} pieces, total weight must be between "
                            f"{base_total_weight} kg and {max_total_weight} kg. (die_over_weight tolerance applied: {percent}%)"
                        )

                else:
                    if payload_weight > allowed_max_weight:
                        raise serializers.ValidationError(
                            f"Cannot create a bundle with weight {payload_weight} kg. "
                            f"For {pieces} pieces, allowed weight with tolerance ({percent:.2f}%): {allowed_max_weight} kg."
                        )

            except WorkOrderDetail.DoesNotExist:
                raise serializers.ValidationError("WorkOrderDetail does not exist.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):

        bundle_no = BundleNumberGenerator().generate_bundle_no()
        validated_data["bundle_no"] = bundle_no
        shift = validated_data.pop("shift", None)

        bundle_inward_instance = BundleInward(**validated_data)

        if shift:
            bundle_inward_instance.capture_shift_snapshot(shift)
        bundle_inward_instance.save()

        return bundle_inward_instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "workorder" in ret:
            ret["workorder"] = WorkOrderSerializers(instance.workorder).data

        if "workorder_detail" in ret:
            ret["workorder_detail"] = WorkOrderDetailSerializers(
                instance.workorder_detail
            ).data

            request = self.context.get("request")
            list_param = (
                request.query_params.get("list", "").lower() if request else "false"
            )

            surface_finish_qs = (
                instance.workorder_detail.surface_finish.all()
                if instance.workorder_detail
                else []
            )

            if list_param in ["true", "1", "yes"]:
                ret["workorder_detail"]["surface_finish"] = list(
                    surface_finish_qs.values_list("name", flat=True)
                )
            else:
                ret["workorder_detail"]["surface_finish"] = list(
                    surface_finish_qs.values_list("id", flat=True)
                )

        return ret


class BundleInwardSortSerializer(serializers.ModelSerializer):
    class Meta:
        model = BundleInward
        fields = [
            "id",
            "bundle_no",
            "packing_date",
            "status",
        ]


class ExcessStockSerializer(BaseModelSerializer):
    avg_weight = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = ExcessStock
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "die_profile",
            "alloy",
            "temper",
            "bundle_inward",
            "length",
            "weight",
            "gross_weight",
            "pieces",
            "shift",
            "hardness_value",
            "remarks",
            "avg_weight",
        ]

    def get_avg_weight(self, data):
        try:
            die = data.die_profile
            length = data.length or 0
            wt_kg_p_mt = die.wt_kg_p_mt if die and die.wt_kg_p_mt else 0

            avg_weight = (length * wt_kg_p_mt) / 1000
            return round(avg_weight, 3)
        except Exception:
            return 0

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "die_profile" in ret:
            ret["die_profile"] = DieSortSerializers(instance.die_profile).data

        if "alloy" in ret:
            ret["alloy"] = AlloySortSerializers(instance.alloy).data

        if "temper" in ret:
            ret["temper"] = TemperSortSerializers(instance.temper).data

        if "bundle_inward" in ret:
            ret["bundle_inward"] = BundleInwardSortSerializer(
                instance.bundle_inward
            ).data

        return ret
