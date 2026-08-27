from rest_framework import serializers

from common.serializers import BaseModelSerializer
from die.models import DiePress

from .models import ShiftLog


class DiePressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiePress
        fields = ["id", "name", "billet_wt_factor"]


def _minutes_to_hms(minutes):
    minutes = minutes or 0
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


class ShiftLogListSerializer(BaseModelSerializer):
    shift_details = serializers.SerializerMethodField(read_only=True)
    press = DiePressSerializer(read_only=True)
    idle_summary = serializers.SerializerMethodField(read_only=True)
    total_running_hrs = serializers.SerializerMethodField(read_only=True)
    total_log_qty = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = ShiftLog
        fields = BaseModelSerializer.Meta.fields + [
            "date",
            "shift",
            "press",
            "supervisor",
            "status",
            "shift_details",
            "idle_summary",
            "total_running_hrs",
            "total_log_qty",
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

    def get_idle_summary(self, obj):
        # ShiftIdleLog was removed; keep response contract stable for the UI.
        return {}

    def get_total_running_hrs(self, obj):
        if obj.shift:
            return _minutes_to_hms(obj.shift.duration_minutes)
        return None

    def get_total_log_qty(self, obj):
        # ShiftUsedLog was removed; keep response contract stable for the UI.
        return 0


class ShiftLogSerializer(BaseModelSerializer):
    shift_details = serializers.SerializerMethodField(read_only=True)
    press_details = DiePressSerializer(source="press", read_only=True)
    idle_summary = serializers.SerializerMethodField(read_only=True)
    total_running_hrs = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = ShiftLog
        fields = BaseModelSerializer.Meta.fields + [
            "date",
            "shift",
            "press",
            "supervisor",
            "status",
            "press_details",
            "idle_summary",
            "total_running_hrs",
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

    def get_idle_summary(self, obj):
        return {}

    def get_total_running_hrs(self, obj):
        if obj.shift:
            return _minutes_to_hms(obj.shift.duration_minutes)
        return None

    def create(self, validated_data):
        # Ignore legacy nested payloads if clients still send them.
        validated_data.pop("shift_idle_log", None)
        validated_data.pop("shift_used_log", None)
        shift = validated_data.get("shift")

        if shift and not shift.is_active:
            raise serializers.ValidationError(
                {"shift": "Invalid or inactive shift selected"}
            )

        shift_log = ShiftLog.objects.create(**validated_data)

        if shift:
            shift_log.capture_shift_snapshot(shift)
            shift_log.save()

        return shift_log

    def update(self, instance, validated_data):
        validated_data.pop("shift_idle_log", None)
        validated_data.pop("shift_used_log", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        shift = validated_data.get("shift", instance.shift)
        if shift:
            instance.capture_shift_snapshot(shift)
            instance.save()

        return instance
