from datetime import datetime, timedelta

from django.db.models import Sum
from rest_framework import serializers

from .models import ShiftMaster


class ShiftMasterSerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField(format="%H:%M:%S")
    end_time = serializers.TimeField(format="%H:%M:%S")

    class Meta:
        model = ShiftMaster
        fields = "__all__"
        read_only_fields = (
            "id",
            "duration_minutes",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )

    def calculate_duration(self, start_time, end_time):
        today = datetime.today().date()

        start_dt = datetime.combine(today, start_time)
        end_dt = datetime.combine(today, end_time)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        return int((end_dt - start_dt).total_seconds() / 60)

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        start_time = attrs.get("start_time", instance.start_time if instance else None)
        end_time = attrs.get("end_time", instance.end_time if instance else None)

        attrs["duration_minutes"] = self.calculate_duration(start_time, end_time)

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["updated_by"] = request.user
        return super().update(instance, validated_data)
