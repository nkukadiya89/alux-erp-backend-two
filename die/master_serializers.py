from rest_framework import serializers

from common.serializers import BaseModelSerializer
from die.models import (
    Die,
    DieCategory,
    DieGroup,
    DiePress,
    DieSize,
    DieSubCategory,
    DieType,
)
from user.serializers import UserQuickSerializer

class DieListSerializers(BaseModelSerializer):
    reference_no = serializers.CharField(source="extrusion_die_info", read_only=True)
    class Meta(BaseModelSerializer.Meta):
        model = Die
        fields = BaseModelSerializer.Meta.fields + ["id", "die_number", "reference_no"]


class BaseNameSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        model = self.Meta.model
        instance = self.instance

        if (
            model.objects.filter(name=value, deleted=0)
            .exclude(id=instance.id if instance else None)
            .exists()
        ):
            raise serializers.ValidationError(
                f"A {model.__name__} with the name '{value}' already exists."
            )

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

    def get_attribute(self, instance):
        instance.created_by
        return super().get_attribute(instance)


class DieGroupDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for DieGroup dropdown API - active and non-archived only"""

    class Meta:
        model = DieGroup
        fields = ["id", "name"]


class DieGroupSerializers(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DieGroup
        fields = "__all__"


class DieCategoryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for DieCategory dropdown API - active and non-archived only"""

    class Meta:
        model = DieCategory
        fields = ["id", "name"]


class DieCategorySerializers(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DieCategory
        fields = BaseModelSerializer.Meta.fields + ["id", "name", "description"]

    def validate(self, attrs):
        instance = self.instance

        name = attrs.get("name", instance.name if instance else None)

        if (
            DieCategory.objects.filter(name=name)
            .exclude(id=instance.id if instance else None)
            .exists()
        ):
            raise serializers.ValidationError(
                {"name": "Die Category with this name already exists."}
            )

        return attrs

class DieSubCategorySerializers(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = DieSubCategory
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
            "description",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        self.context.get("request")
        instance = self.instance

        name = attrs.get("name", instance.name if instance else None)

        if (
            DieSubCategory.objects.filter(name=name)
            .exclude(id=instance.id if instance else None)
            .exists()
        ):
            raise serializers.ValidationError(
                {"name": "Die Sub Category with this name already exists."}
            )

        return attrs

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

    def get_die_count(self, obj):
        return obj.dies.count()


class DieTypeSerializers(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DieType
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "name",
            "description",
        ]


class DieSizeDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for DieSize dropdown API - active and non-archived only"""

    class Meta:
        model = DieSize
        fields = ["id", "diameter", "thickness"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get("diameter") is not None and ret.get("thickness") is not None:
            ret["display"] = f"{ret['diameter']} - {ret['thickness']}"
        elif ret.get("diameter") is not None:
            ret["display"] = str(ret["diameter"])
        elif ret.get("thickness") is not None:
            ret["display"] = str(ret["thickness"])
        else:
            ret["display"] = ""
        return ret


class DieSizeSerializers(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DieSize
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "diameter",
            "thickness",
        ]

    def validate(self, data):
        """Validate diameter and thickness combination uniqueness"""
        diameter = data.get("diameter")
        thickness = data.get("thickness")

        diameter = data.get("diameter")
        thickness = data.get("thickness")

        if diameter is not None and thickness is not None:
            queryset = DieSize.objects.filter(
                diameter=diameter, thickness=thickness, deleted=False
            )

            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError(
                    "DieSize with this diameter and thickness combination already exists."
                )

        return data

    def get_die_tool_count(self, obj):
        return obj.dietool_diesize.count()

    def get_die_count(self, obj):
        die_tools = obj.dietool_diesize.select_related("die")
        unique_die_ids = {dt.die.id for dt in die_tools if dt.die}
        return len(unique_die_ids)


class DiePressDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for DiePress dropdown API - active and non-archived only"""

    class Meta:
        model = DiePress
        fields = ["id", "code", "name"]


class DiePressSerializers(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DiePress
        fields = "__all__"
