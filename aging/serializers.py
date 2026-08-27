from rest_framework import serializers
from aging.models import AgeingBatch, AgeingBatchDetail, AgeingTemperatureLog
from common.serializers import BaseModelSerializer
from die.models import Die, DieTool
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from production.models import Production
from production.serializers import ProductionSerializer
from shift.models import ShiftMaster
from utils.generate_number import generate_ageing_batch_no

class AgeingListSerializer(BaseModelSerializer):
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = AgeingBatch
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "batch_no",
            "heat_treatment_no",
            "temperature",
            "ageing_date",
            "soaking_time",
            "shift",
            "shift_details",
            "start_time",
            "end_time",
            "cycle_time",
            "furnace_no",
            "status",
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


class AgeingTemperatureLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeingTemperatureLog
        fields = [
            "id",
            "log_time",
            "zone1_temp",
            "zone2_temp",
            "zone3_temp",
            "zone4_temp",
            "deviation",
            "remarks",
        ]


class ProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Production
        fields = ["id", "production_no"]


class DieToolSerializer(serializers.ModelSerializer):
    die_number = serializers.CharField(source="die.die_number", read_only=True)

    class Meta:
        model = DieTool
        fields = ["id", "tool_number", "die_number"]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Die
        fields = ["id", "die_number"]


class AgeingBatchDetailSerializer(serializers.ModelSerializer):
    alloy_detail = AlloySortSerializers(source="alloy", read_only=True)
    temper_detail = TemperSortSerializers(source="temper", read_only=True)
    workorder_no = serializers.CharField(
        source="production_no.workorder.order_no",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AgeingBatchDetail
        fields = [
            "id",
            "production_no",
            "side",
            "depth",
            "position",
            "rack_no",
            "die_no",
            "section_no",
            "workorder_no",
            "cast_no",
            "cut_length_mm",
            "pieces",
            "remark",
            "weight_per_piece",
            "total_weight",
            "alloy",
            "alloy_detail",
            "temper",
            "temper_detail",
        ]
        extra_kwargs = {
            "production_no": {"required": False, "allow_null": True},
            "die_no": {"required": False, "allow_null": True},
            "alloy": {"required": False, "allow_null": True},
            "temper": {"required": False, "allow_null": True},
            "section_no": {"required": False, "allow_null": True},
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "production_no" in ret:
            ret["production_no"] = ProductionSerializer(instance.production_no).data

        if "section_no" in ret:
            ret["section_no"] = SectionSerializer(instance.section_no).data

        if "die_no" in ret:
            ret["die_no"] = DieToolSerializer(instance.die_no).data
        return ret


class AgeingBatchSerializer(BaseModelSerializer):
    batch_no = serializers.CharField(required=False)
    batch_details = AgeingBatchDetailSerializer(many=True, required=False)
    temperature_logs = AgeingTemperatureLogSerializer(many=True, required=False)
    soaking_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = AgeingBatch
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "batch_no",
            "heat_treatment_no",
            "ageing_date",
            "shift",
            "shift_details",
            "furnace_no",
            "temperature",
            "soaking_time",
            "start_time",
            "end_time",
            "gas_reading_start",
            "gas_reading_end",
            "cycle_time",
            "status",
            "batch_details",
            "temperature_logs",
        ]

    def validate_batch_no(self, value):
        if self.instance:
            if (
                AgeingBatch.objects.filter(batch_no=value)
                .exclude(id=self.instance.id)
                .exists()
            ):
                raise serializers.ValidationError("Batch number already exists.")
        else:
            if AgeingBatch.objects.filter(batch_no=value).exists():
                raise serializers.ValidationError("Batch number already exists.")
        return value

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
        batch_details_data = validated_data.pop("batch_details", [])
        temperature_logs_data = validated_data.pop("temperature_logs", [])
        shift = validated_data.pop("shift", None)

        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift": "Selected shift is inactive"})

        validated_data["batch_no"] = generate_ageing_batch_no()

        ageing_batch = AgeingBatch(**validated_data)

        if shift:
            ageing_batch.capture_shift_snapshot(shift)

        ageing_batch.save()

        for detail_data in batch_details_data:
            AgeingBatchDetail.objects.create(ageing_batch=ageing_batch, **detail_data)

        for log_data in temperature_logs_data:
            AgeingTemperatureLog.objects.create(ageing_batch=ageing_batch, **log_data)

        # Advance process tracking to AGEING when applicable
        try:
            from workorder.process_tracking import advance_process

            request = self.context.get("request")
            user = None
            if request is not None and getattr(request, "user", None):
                user = request.user if getattr(request.user, "is_authenticated", False) else None
            if user is None:
                user = validated_data.get("created_by")

            for detail_data in batch_details_data:
                production = detail_data.get("production_no")
                if not production:
                    continue
                planning = getattr(production, "planning", None)
                wod = planning.workorder_detail if planning else None
                if not wod:
                    continue
                advance_process(
                    workorder_detail=wod,
                    planning=planning,
                    stage="AGEING",
                    user=user,
                    remarks=f"Ageing batch {ageing_batch.batch_no}",
                )
        except Exception:
            pass

        return ageing_batch

    def update(self, instance, validated_data):
        batch_details_data = validated_data.pop("batch_details", None)
        temperature_logs_data = validated_data.pop("temperature_logs", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if batch_details_data is not None:
            existing_detail_ids = [
                detail.get("id") for detail in batch_details_data if detail.get("id")
            ]
            instance.batch_details.exclude(id__in=existing_detail_ids).delete()

            for detail_data in batch_details_data:
                detail_id = detail_data.pop("id", None)
                if detail_id:
                    AgeingBatchDetail.objects.filter(
                        id=detail_id, ageing_batch=instance
                    ).update(**detail_data)
                else:
                    AgeingBatchDetail.objects.create(
                        ageing_batch=instance, **detail_data
                    )

        if temperature_logs_data is not None:
            existing_log_ids = [
                log.get("id") for log in temperature_logs_data if log.get("id")
            ]
            instance.temperature_logs.exclude(id__in=existing_log_ids).delete()

            for log_data in temperature_logs_data:
                log_id = log_data.pop("id", None)
                if log_id:
                    AgeingTemperatureLog.objects.filter(
                        id=log_id, ageing_batch=instance
                    ).update(**log_data)
                else:
                    AgeingTemperatureLog.objects.create(
                        ageing_batch=instance, **log_data
                    )

        return instance
