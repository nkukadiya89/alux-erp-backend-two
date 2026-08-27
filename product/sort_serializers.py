from rest_framework import serializers

from common.models import SectionType
from product.models import Alloy, StandardMaster, Temper

class StandardMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardMaster
        fields = ["name"]


class SectionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionType
        fields = ["name"]

class TemperSortSerializers(serializers.ModelSerializer):
    standard = StandardMasterSerializer(read_only=True)
    section_type = SectionTypeSerializer(read_only=True)
    class Meta:
        model = Temper
        fields = [
            "id",
            "alloy",
            "standard",
            "section_type",
            "temper_code_new",
            "section_thickness_over",
            "section_thickness_upto"
        ]

class AlloySortSerializers(serializers.ModelSerializer):
    standard = StandardMasterSerializer(read_only=True)

    class Meta:
        model = Alloy
        fields = [
            "id",
            "alloy_code",
            "standard", 
        ]
