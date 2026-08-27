from rest_framework import serializers
from common.master_serializers import UOMDropdownSerializer
from common.serializers import DepartmentDropdownSerializer
from product.serializers import ItemDropdownSerializer
from .models import MaterialRequest, MaterialRequestDetail


class MaterialRequestDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = MaterialRequestDetail
        fields = [
            "id", 
            "item",
            "description", 
            "unit",
            "required_qty", 
            "available_qty",
            "issue_qty",
            "remarks",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "item" in ret and instance.item:
            ret["item"] = ItemDropdownSerializer(instance.item).data

        if "unit" in ret and instance.unit:
            ret["unit"] = UOMDropdownSerializer(instance.unit).data

        return ret


class MaterialRequestSerializer(serializers.ModelSerializer):
    material_request_detail = MaterialRequestDetailSerializer(many=True, required=False)

    class Meta:
        model = MaterialRequest
    
        fields = [
            "id", 
            "request_no", 
            "date", 
            "department", 
            "remarks", 
            "material_request_detail",
        ]

    def create(self, validated_data):
        details_data = validated_data.pop('material_request_detail', [])
        material_request = MaterialRequest.objects.create(**validated_data)
        
        for detail_data in details_data:
            MaterialRequestDetail.objects.create(material_request=material_request, **detail_data)
            
        return material_request


    def update(self, instance, validated_data):
        details_data = validated_data.pop("material_request_detail", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if details_data is not None:
            instance.material_request_detail.all().delete()

            for detail in details_data:
                MaterialRequestDetail.objects.create(
                    material_request=instance,
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


class MaterialRequestListSerializer(serializers.ModelSerializer):
    total_items = serializers.IntegerField(read_only=True)
    class Meta:
        model = MaterialRequest
        fields = [
            "id",
            "request_no",
            "date",
            "department",
            "remarks",
            "total_items",
        ]

    def to_representation(self, instance):
            ret = super().to_representation(instance)
            if "department" in ret and instance.department:
                ret["department"] = DepartmentDropdownSerializer(
                    instance.department
                ).data
    
            return ret