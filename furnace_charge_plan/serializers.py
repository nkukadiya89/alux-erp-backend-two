from rest_framework import serializers
from .models import FurnaceChargePlan, FurnaceChargePlanDetail


class FurnaceChargePlanDetailSerializer(serializers.ModelSerializer):

    material_name = serializers.CharField( source="material.name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = FurnaceChargePlanDetail
        fields = "__all__"


class FurnaceChargePlanSerializer(serializers.ModelSerializer):
    details = FurnaceChargePlanDetailSerializer(source="furnacechargeplandetail_set", many=True, read_only=True)
    furnace_name = serializers.CharField(source="furnace.name", read_only=True)
    alloy_name = serializers.CharField(source="alloy_type.name", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.username", read_only=True)

    class Meta:
        model = FurnaceChargePlan
        fields = "__all__"