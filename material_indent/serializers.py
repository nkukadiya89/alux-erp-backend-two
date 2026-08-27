from rest_framework import serializers

from common.serializers import DepartmentDropdownSerializer
from common.master_serializers import UOMDropdownSerializer
from store.serializers import StoreDropdownSerializer

from .models import MaterialIndent, MaterialIndentDetail


class MaterialDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialIndentDetail
        fields = [
            "id",
            "material_indent",
            "item",
            "available_qty",
            "location",
            "requested_qty",
            "store",
            "uom",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "store" in ret and instance.store:
            ret["store"] = StoreDropdownSerializer(instance.store).data

        if "uom" in ret and instance.uom:
            ret["uom"] = UOMDropdownSerializer(instance.uom).data

        return ret


class MaterialIndentSerializer(serializers.ModelSerializer):
    material_indent = MaterialDetailSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = MaterialIndent
        fields = [
            "id",
            "indent_no",
            "department",
            "required_date",
            "material_indent",
            "priority",
            "remarks",
        ]

    def create(self, validated_data):
        material_indent_data = validated_data.pop(
            "material_indent",
            []
        )

        material_indent = MaterialIndent.objects.create(
            **validated_data
        )

        for detail in material_indent_data:
            MaterialIndentDetail.objects.create(
                material_indent=material_indent,
                **detail
            )

        return material_indent

    def update(self, instance, validated_data):
        material_indent_data = validated_data.pop(
            "material_indent",
            None
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if material_indent_data is not None:
            instance.material_indent.all().delete()

            for detail in material_indent_data:
                MaterialIndentDetail.objects.create(
                    material_indent=instance,
                    **detail
                )

        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        if "department" in ret and instance.department:
            ret["department"] = DepartmentDropdownSerializer(
                instance.department
            ).data

        return ret


class MaterialIndentListSerializer(serializers.ModelSerializer):
    department = serializers.CharField(
        source="department.department_name",
        read_only=True
    )

    material_indent = MaterialDetailSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = MaterialIndent
        fields = [
            "id",
            "indent_no",
            "department",
            "required_date",
            "priority",
            "remarks",
            "material_indent",
        ]