from common.serializers import BaseModelSerializer
from die.models import Die, DieTool
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from user.serializers import UserQuickSerializer
from utils.generate_number import generate_failure_no, generate_nitriding_batch_no
from .models import (
    ActivityMaster,
    AnalysisMethod,
    CorrectionType, 
    DieFailureLog, 
    DieProductionLog, 
    DieMaintenanceLog, 
    DieNitridingBatch,
    DieNitridingBatchDetail,
    DieTrialLog, 
    MaintenanceType,
    ReasonForMaintenance,
    CorrectionHistory,
    ReasonForCorrection,
    CorrectionInspectionType
)
from rest_framework import serializers
from shift.models import ShiftMaster
from die.sort_serializers import DiePressSortSerializers, DieToolSortSerializer
from django.db import transaction
 
class MaintenanceTypeSerializer(BaseModelSerializer):
    class Meta:
        model = MaintenanceType
        fields = "__all__"

class ReasonForMaintenanceSerializer(BaseModelSerializer):
    class Meta:
        model = ReasonForMaintenance
        fields = "__all__"

class DieProductionLogSerializer(BaseModelSerializer):
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = DieProductionLog
        fields = "__all__"
 
    def create(self, validated_data):
        shift = validated_data.get("shift")
 
        instance = DieProductionLog(**validated_data)
 
        if shift:
            instance.capture_shift_snapshot(shift)
 
        instance.save()
        return instance
   
    def get_shift_details(self, obj):
        if obj.shift_name_snapshot:
            return {
                "id": obj.shift.id if obj.shift else None,
                "name": obj.shift_name_snapshot,
                "start_time": obj.shift_start_snapshot,
                "end_time": obj.shift_end_snapshot,
            }
        return None
   
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if "press" in ret:
            ret["press"] = DiePressSortSerializers(instance.press).data
        if "die_tool" in ret:
            ret["die_tool"] = DieToolSortSerializer(instance.die_tool).data
 
        return ret
 
class DieMaintenanceLogSerializer(BaseModelSerializer):
    class Meta:
        model = DieMaintenanceLog
        fields = "__all__"
 
 
class DieMaintenanceLogListSerializer(BaseModelSerializer):
    maintenance_type = serializers.CharField(source="maintenance_type.name", read_only=True)
    reason_for_maintenance = serializers.CharField(source="reason_for_maintenance.name", read_only=True)
    die_tool = DieToolSortSerializer(read_only=True)
    inspection_done_by = serializers.CharField(source="inspection_done_by.first_name", read_only=True)
    after_maintenance_done_by = serializers.CharField(source="after_maintenance_done_by.first_name", read_only=True)

    class Meta:
        model = DieMaintenanceLog
        fields = (
            "id",
            "die_tool",
            "date",
            "die_life_percentage",
            "inspection_done_by",
            "after_maintenance_done_by",
            "maintenance_type",
            "reason_for_maintenance",
            "hardness_before",
            "hardness_after",
            "inspection_result",
            "inspection_type",
            "remarks",
        )

class DieNitridingBatchDetailSerializer(BaseModelSerializer):
    class Meta:
        model = DieNitridingBatchDetail
        fields = [
            "id",
            "batch",
            "section",
            "die_tool",
            "die_plate",
            "die_mandrel",
            "die_weight",
        ]
        read_only_fields = ["id", "batch"]

class DieNitridingBatchSerializer(BaseModelSerializer):
    details = DieNitridingBatchDetailSerializer(many=True, required=False)
    class Meta:
        model = DieNitridingBatch
        fields = "__all__"

    def create(self, validated_data):
        from utils.generate_number import generate_nitriding_batch_no
        details_data = validated_data.pop("details", [])

        validated_data["batch_no"] = generate_nitriding_batch_no()

        instance = DieNitridingBatch.objects.create(
            **validated_data
        )

        for detail_data in details_data:
            DieNitridingBatchDetail.objects.create(
                batch=instance,
                **detail_data
            )

        return instance 

    @transaction.atomic
    def update(self, instance, validated_data):

        details_data = validated_data.pop(
            "details",
            None
        )


        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        
        if details_data is not None:

            # Existing DB details
            existing_details = {
                detail.id: detail
                for detail in instance.details.all()
            }

            payload_detail_ids = set()

            for detail_data in details_data:

                detail_id = detail_data.pop(
                    "id",
                    None
                )

               
                if detail_id:

                    payload_detail_ids.add(detail_id)

                    detail_instance = existing_details.get(
                        detail_id
                    )

                    if not detail_instance:
                        raise serializers.ValidationError({
                            "details": [
                                f"Detail ID {detail_id} does not belong to this batch."
                            ]
                        })

                    for attr, value in detail_data.items():
                        setattr(
                            detail_instance,
                            attr,
                            value
                        )

                    detail_instance.save()

               
                else:

                    DieNitridingBatchDetail.objects.create(
                        batch=instance,
                        **detail_data
                    )

            for detail_id, detail_instance in existing_details.items():

                if detail_id not in payload_detail_ids:
                    detail_instance.delete()

        return instance      

class DieNitridingBatchListSerializer(BaseModelSerializer):
    furnace = serializers.SerializerMethodField()
    operator = UserQuickSerializer(read_only=True)
    class Meta:
        model = DieNitridingBatch
        fields = "__all__"

    def get_furnace(self, obj):
        if not obj.furnace:
            return None

        return {
            "id": obj.furnace.id,
            "furnace_code": obj.furnace.furnace_code,
            "furnace_name": obj.furnace.furnace_name
        }


class DieTrialLogSerializer(BaseModelSerializer):
    class Meta:
        model = DieTrialLog
        fields = "__all__"
 
 
    def create(self, validated_data):
        from utils.generate_number import generate_trial_no
        shift = validated_data.get("shift")
        validated_data["trial_no"] = generate_trial_no()
        instance = DieTrialLog(**validated_data)
 
        if shift:
            instance.capture_shift_snapshot(shift)
 
        instance.save()
        return instance
 
 
class DieTrialLogListSerializer(BaseModelSerializer):
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    die_tool = DieToolSortSerializer(read_only=True)
    alloy = AlloySortSerializers(read_only=True)
    temper = TemperSortSerializers(read_only=True)  
    approved_by = UserQuickSerializer(read_only=True)  
 
    class Meta(BaseModelSerializer.Meta):
        model = DieTrialLog
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "trial_date",
            "trial_type",
            "trial_no",
            "alloy",
            "temper",
            "shift",
            "shift_details",
            "die_tool",
            "result",
            "billet_size",
            "suggestion",
            "approved_by",
            "total_extrude_kg",
            "trial_count",
            "remarks"
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
 
    def get_approved_by_detail(self, obj):
        if obj.approved_by:
            return {
                "id": obj.approved_by.id,
                "first_name": obj.approved_by.first_name,
                "last_name": obj.approved_by.last_name,
            }
        return None


class CorrectionInspectionTypeSerializer(BaseModelSerializer):
    class Meta:
        model = CorrectionInspectionType
        fields = "__all__"


class ReasonForCorrectionSerializer(BaseModelSerializer):
    class Meta:
        model = ReasonForCorrection
        fields = "__all__"


class CorrectionTypeSerializer(BaseModelSerializer):
    class Meta:
        model = CorrectionType
        fields = "__all__"

class ActivityMasterSerializer(BaseModelSerializer):
    class Meta:
        model = ActivityMaster
        fields = "__all__"


class CorrectionHistorySerializer(BaseModelSerializer):
    class Meta:
        model = CorrectionHistory
        fields = "__all__"
 
    def create(self, validated_data):
        from utils.generate_number import generate_correction_request_no
 
        validated_data["correction_request_no"] = generate_correction_request_no()
 
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["activity"] = ActivityMasterSerializer(
            instance.activity.all(),
            many=True
        ).data

        return data

class CorrectionHistoryListSerializer(BaseModelSerializer):
    die_tool = DieToolSortSerializer(read_only=True)
    correction_done_by = serializers.CharField(source="correction_done_by.first_name", read_only=True)
    correction_type = serializers.CharField(source="correction_type.name", read_only=True)
    inspection_type = serializers.CharField(source="inspection_type.name", read_only=True)
    inspection_by = serializers.CharField(source="inspection_by.first_name", read_only=True)
    reason_for_correction = serializers.CharField(source="reason_for_correction.name", read_only=True)
    class Meta:
        model = CorrectionHistory
        fields = [
            "id",
            "die_tool",
            "date",
            "correction_type",
            "inspection_type",
            "inspection_by",
            "reason_for_correction",
            "problem_description",
            "correction_request_no",
            "reason_for_correction",
            "correction_done_by",
            "inspection_result",
            "die_life_percentage",
            "remarks"
        ]


class AnalysisMethodSerializer(BaseModelSerializer):
    class Meta:
        model = AnalysisMethod
        fields = "__all__"


class DieFailureLogSerializer(BaseModelSerializer):
    broken_part = serializers.ListField(
        child=serializers.ChoiceField(choices=DieFailureLog.BROKEN_PART_CHOICES),
        required=False, allow_empty=True
    )
    class Meta:
        model = DieFailureLog
        fields = "__all__"
 
    def create(self, validated_data):
        shift = validated_data.get("shift")
        validated_data["failure_no"] = generate_failure_no()

        instance = DieFailureLog(**validated_data)
        if shift:
            instance.capture_shift_snapshot(shift)
 
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["analysis_method"] = AnalysisMethodSerializer(instance.analysis_method).data
        return data

    
class DieFailureLogListSerializer(BaseModelSerializer):
    die_tool = DieToolSortSerializer(read_only=True)
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    broken_part = serializers.ListField(
        child=serializers.ChoiceField(choices=DieFailureLog.BROKEN_PART_CHOICES),
        required=False, allow_empty=True
    )
 
    class Meta:
        model = DieFailureLog
        fields = [
            "id",
            "die_tool",
            "failure_no",
            "severity",
            "failure_date",
            "failure_type",
            "source",
            "remarks",
            "downtime_hours",
            "broken_part",
            "root_cause",
            "action_taken",
            "start_time",
            "end_time",
            "shift",
            "shift_details"
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
 
 