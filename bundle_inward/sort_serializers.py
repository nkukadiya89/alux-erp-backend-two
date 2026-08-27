from rest_framework import serializers

from bundle_inward.models import BundleInward
from common.serializers import (
    BaseModelSerializer,
    JobWorkSerializer,
    PackingModeSerializer,
)
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers


class BundleInwardListSerializer(BaseModelSerializer):
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
    workorder = serializers.CharField(source="workorder.order_no", read_only=True)
    die_description = serializers.SerializerMethodField()
    shift = serializers.CharField(source="shift.shift_name", read_only=True)

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
            "shift",
            "length",
            "pieces",
            "weight",
            "avg_weight",
            "gross_weight",
            "packing_date",
            "dispatch_date",
            "hardness",
            "die_description",
            "remarks",
            "status",
            "packing_mode",
            "surface_finish",
            "alloy",
            "temper",
        ]

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

    def get_die_description(self, obj):
        die = getattr(obj.workorder_detail, "die_profile", None)
        if die:
            dimensions = []
            for dim in ["dimension1", "dimension2", "dimension3", "dimension4"]:
                value = getattr(die, dim, None)
                if value is not None:
                    if value and value != 0:
                        dimensions.append(str(value))
            dimension_text = " X ".join(dimensions)
            if die.description:
                return (
                    f"{die.description} ({dimension_text})"
                    if dimension_text
                    else die.description
                )
            return dimension_text
        return ""
