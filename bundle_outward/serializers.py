from rest_framework import serializers

from bundle_outward.models import (
    BundleOutward,
    BundleOutwardInward,
    BundleOutwardOutward,
)
from common.serializers import BaseModelSerializer
from shift.models import ShiftMaster
from utils.generate_number import generate_slip_no
from vehicle_master.models import VehicleMaster
from vehicle_master.serializer import VehicleMasterSortSerializer
from workorder.serializers import WorkOrderSerializers


class BundleOutwardSerializer(BaseModelSerializer):
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    finalized_bundle_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    outward_bundle_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    vehicle_no = serializers.PrimaryKeyRelatedField(
        queryset=VehicleMaster.objects.all(), required=False, allow_null=True
    )
    vehicle_detail = VehicleMasterSortSerializer(source="vehicle_no", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = BundleOutward
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "workorder",
            "slip_no",
            "date_prepared",
            "shift",
            "shift_details",
            "party_name",
            "vehicle_no",
            "vehicle_detail",
            "dispatch_to",
            "approved",
            "remarks",
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
        validated_data["slip_no"] = generate_slip_no(self)

        finalized_bundle_ids = validated_data.pop("finalized_bundle_ids", [])
        outward_bundle_ids = validated_data.pop("outward_bundle_ids", [])

        shift = validated_data.get("shift", None)

        bundle_outward = BundleOutward(**validated_data)

        if shift:
            bundle_outward.capture_shift_snapshot(shift)

        bundle_outward.save()

        if finalized_bundle_ids:
            from bundle_inward.models import BundleInward

            for bundle_id in finalized_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    BundleOutwardInward.objects.create(
                        bundle_outward=bundle_outward, bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        if outward_bundle_ids:
            from bundle_inward.models import BundleInward

            for bundle_id in outward_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    BundleOutwardOutward.objects.create(
                        bundle_outward=bundle_outward, bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        return bundle_outward

    def update(self, instance, validated_data):
        finalized_bundle_ids = validated_data.pop("finalized_bundle_ids", None)
        outward_bundle_ids = validated_data.pop("outward_bundle_ids", None)

        bundle_outward = super().update(instance, validated_data)

        if finalized_bundle_ids is not None:
            BundleOutwardInward.objects.filter(bundle_outward=bundle_outward).delete()

            from bundle_inward.models import BundleInward

            for bundle_id in finalized_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    BundleOutwardInward.objects.create(
                        bundle_outward=bundle_outward, bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        if outward_bundle_ids is not None:
            BundleOutwardOutward.objects.filter(bundle_outward=bundle_outward).delete()

            from bundle_inward.models import BundleInward

            for bundle_id in outward_bundle_ids:
                try:
                    bundle = BundleInward.objects.get(id=bundle_id, deleted=False)
                    BundleOutwardOutward.objects.create(
                        bundle_outward=bundle_outward, bundle_inward=bundle
                    )
                except BundleInward.DoesNotExist:
                    pass

        return bundle_outward

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "workorder" in ret:
            ret["workorder"] = WorkOrderSerializers(instance.workorder).data

        return ret
