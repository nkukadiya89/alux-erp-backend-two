from rest_framework import serializers

from common.serializers import BaseModelSerializer
from vehicle_master.models import VehicleMaster
from vehicle_master.serializer import VehicleMasterSortSerializer
from warehouse.models import Warehouse, WarehouseBundleInward, WarehouseBundleOutward
from workorder.serializers import WorkOrderSortSerializers
from shift.models import ShiftMaster

class WarehouseSerializers(BaseModelSerializer):
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    vehicle_no = serializers.PrimaryKeyRelatedField(
        queryset=VehicleMaster.objects.all(), required=False, allow_null=True
    )
    vehicle_detail = VehicleMasterSortSerializer(source="vehicle_no", read_only=True)
    finalized_bundle_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    outward_bundle_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta(BaseModelSerializer.Meta):
        model = Warehouse
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "workorder",
            "vehicle_no",
            "vehicle_detail",
            "party_name",
            "shift",
            "shift_details",
            "remarks",
            "dispatched",
            "added_for_outword",
            "finalized_bundle_ids",
            "outward_bundle_ids",
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

    def create(self, validated_data):
        finalized_bundle_ids = validated_data.pop("finalized_bundle_ids", [])
        outward_bundle_ids = validated_data.pop("outward_bundle_ids", [])

        shift = validated_data.get("shift", None)
        warehouse = Warehouse(**validated_data)

        if shift:
            warehouse.capture_shift_snapshot(shift)

        warehouse.save()

        if finalized_bundle_ids:
            from bundle_inward.models import BundleInward

            for bundle_id in finalized_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    WarehouseBundleInward.objects.create(
                        warehouse=warehouse,
                        bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        if outward_bundle_ids:
            from bundle_inward.models import BundleInward

            for bundle_id in outward_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    WarehouseBundleOutward.objects.create(
                        warehouse=warehouse,
                        bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        return warehouse

    def update(self, instance, validated_data):
        finalized_bundle_ids = validated_data.pop("finalized_bundle_ids", None)
        outward_bundle_ids = validated_data.pop("outward_bundle_ids", None)

        warehouse = super().update(instance, validated_data)

        if finalized_bundle_ids is not None:
            WarehouseBundleInward.objects.filter(warehouse=warehouse).delete()

            from bundle_inward.models import BundleInward

            for bundle_id in finalized_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    WarehouseBundleInward.objects.create(
                        warehouse=warehouse, bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        if outward_bundle_ids is not None:
            WarehouseBundleOutward.objects.filter(warehouse=warehouse).delete()

            from bundle_inward.models import BundleInward

            for bundle_id in outward_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    WarehouseBundleOutward.objects.create(
                        warehouse=warehouse, bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        return warehouse

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "workorder" in ret:
            ret["workorder"] = WorkOrderSortSerializers(instance.workorder).data

        return ret
