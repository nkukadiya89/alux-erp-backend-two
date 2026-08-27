from rest_framework import serializers

from die.master_serializers import BaseNameSerializer
from die.models import (
    ConversionRate,
    Die,
    DieCategory,
    DieGroup,
    DiePress,
    DieSize,
    DieSubCategory,
    DieTool,
)


class DieGroupSortSerializers(BaseNameSerializer):
    class Meta:
        model = DieGroup
        fields = [
            "id",
            "name",
        ]


class DieCategorySortSerializers(BaseNameSerializer):
    class Meta:
        model = DieCategory
        fields = [
            "id",
            "name",
        ]


class DieSubCategorySortSerializers(serializers.ModelSerializer):
    class Meta:
        model = DieSubCategory
        fields = [
            "id",
            "name",
        ]


class DieSubCategorySortSerializers(serializers.ModelSerializer):
    class Meta:
        model = DieSubCategory
        fields = [
            "id",
            "name",
        ]


class DieSizeSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = DieSize
        fields = [
            "id",
            "diameter",
            "thickness",
        ]


class DiePressSortSerializers(BaseNameSerializer):
    class Meta:
        model = DiePress
        fields = [
            "id",
            "name",
        ]


class DieSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = Die
        fields = [
            "id",
            "die_number",
            "dimension1",
            "dimension2",
            "dimension3",
            "die_type",
            "wt_kg_p_mt",
            "die_diagram",
            "description",
            "front_end_process_loss_mm",
            "back_end_process_loss_mm",
            "stretching_head_loss_mm",
            "stretching_tail_loss_mm",
            "total_process_loss_mm",
            "total_process_loss_meter"
        ]


class DieSortListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Die
        fields = [
            "die_number",
            "die_diagram",
            "dimension1",
            "dimension2",
            "dimension3",
        ]


class ConversionRateSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = ConversionRate
        fields = ["id", "conversion"]


class DieToolSortSerializer(serializers.ModelSerializer):
    section_no = serializers.CharField(source="die.die_number", read_only=True)
    class Meta:
        model = DieTool
        fields = ["id", "tool_number", "section_no", "die_oblique_number"]