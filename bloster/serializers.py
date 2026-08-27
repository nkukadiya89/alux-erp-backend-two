from rest_framework import serializers
from common.serializers import BaseModelSerializer
from die.models import Die
from die.sort_serializers import DiePressSortSerializers

from .models import BlosterMaster, BlosterType


class DieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Die
        fields = [
            "id",
            "die_number",
        ]


class BlosterTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlosterType
        fields = ["id", "name", "status"]


class BlosterMasterSerializer(BaseModelSerializer):
    related_dies = serializers.SerializerMethodField()
    die_tool_count = serializers.SerializerMethodField()
    die_count = serializers.SerializerMethodField()

    type = serializers.PrimaryKeyRelatedField(
        queryset=BlosterType.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = BlosterMaster
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "bloster_no",
            "bloster_image",
            "size",
            "diameter_mm",
            "thickness_mm",
            "type",
            "description",
            "press",
            "autocard",
            "pdf",
            "related_dies",
            "die_tool_count",
            "die_count",
        ]

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

    def get_related_dies(self, obj):
        die_map = {}

        for tool in (
            list(obj.dietool_bloster_first.all())
            + list(obj.dietool_bloster_second.all())
            + list(obj.dietool_bloster_third.all())
        ):
            if tool.die:
                die_map[tool.die.id] = tool.die

        return DieSerializer(die_map.values(), many=True).data

    def get_die_tool_count(self, obj):
        return obj.first_count + obj.second_count + obj.third_count

    def get_die_count(self, obj):
        die_ids = {
            tool.die_id
            for tool in (
                list(obj.dietool_bloster_first.all())
                + list(obj.dietool_bloster_second.all())
                + list(obj.dietool_bloster_third.all())
            )
            if tool.die_id
        }

        return len(die_ids)

    def validate_bloster_no(self, value):
        if value:
            value = value.strip()
            queryset = BlosterMaster.objects.filter(
                bloster_no__iexact=value, deleted=False
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Bloster number already exists.")
        return value

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "press" in ret:
            ret["press"] = DiePressSortSerializers(instance.press).data

        if instance.type:
            ret["type"] = BlosterTypeSerializer(instance.type).data

        return ret


class BlosterMasterSortSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type.name", read_only=True)

    class Meta:
        model = BlosterMaster
        fields = ["id", "bloster_no", "type"]


class BlosterMasterDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlosterMaster
        fields = ["id", "bloster_no", "type"]
