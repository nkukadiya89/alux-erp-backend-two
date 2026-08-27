from rest_framework import serializers
from decimal import Decimal

from common.serializers import BaseModelSerializer
from nalco.models import NalcoMaster


class NalcoMasterSerializers(BaseModelSerializer):
    rate_per_kg = serializers.SerializerMethodField()
    diff_kg = serializers.SerializerMethodField()
    diff_mt = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = NalcoMaster
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "date",
            "ignot_grade",
            "rate_per_mt",
            "rate_per_kg",
            "adjustment_type",
            "adjustment_value",
            "final_rate_kg",
            "final_rate_mt",
            "diff_kg",
            "diff_mt",
            "percentage",
        ]

    def get_rate_per_kg(self, obj):
        if obj.rate_per_mt:
            return format(obj.rate_per_mt / Decimal(1000), ".2f")
        return "0.00"

    def get_previous(self, obj):
        if hasattr(obj, "_previous"):
            return obj._previous

        obj._previous = (
            NalcoMaster.objects.filter(deleted=False, date__lt=obj.date)
            .order_by("-date")
            .first()
        )
        return obj._previous

    def get_diff_kg(self, obj):
        prev = self.get_previous(obj)
        if not prev or not prev.rate_per_mt or not obj.rate_per_mt:
            return 0

        current = obj.rate_per_mt / Decimal(1000)
        previous = prev.rate_per_mt / Decimal(1000)

        return round(current - previous, 2)

    def get_diff_mt(self, obj):
        diff_kg = self.get_diff_kg(obj)
        return round(Decimal(str(diff_kg)) * Decimal(1000), 2)

    def get_percentage(self, obj):
        prev = self.get_previous(obj)
        if not prev or not prev.rate_per_mt or not obj.rate_per_mt:
            return 0

        current = obj.rate_per_mt / Decimal(1000)
        previous = prev.rate_per_mt / Decimal(1000)

        if previous == 0:
            return 0

        percent = ((current - previous) / previous) * 100
        return round(percent, 2)

    def create(self, validated_data):
        ignot_grade = validated_data.get("ignot_grade")
        date = validated_data.get("date")
        rate_per_mt = validated_data.get("rate_per_mt")

        previous = (
            NalcoMaster.objects.filter(
                ignot_grade=ignot_grade,
                deleted=False,
                date__lt=date,
            )
            .order_by("-date")
            .first()
        )

        if previous and previous.rate_per_mt and rate_per_mt:
            current_kg = rate_per_mt / Decimal(1000)
            previous_kg = previous.rate_per_mt / Decimal(1000)

            diff_kg = round(current_kg - previous_kg, 2)
            diff_mt = round(diff_kg * Decimal(1000), 2)

            final_rate_kg = round(current_kg, 2)
            final_rate_mt = round(rate_per_mt, 2)

            adjustment_value = abs(diff_kg)

            if diff_kg > 0:
                adjustment_type = "Increase"
            elif diff_kg < 0:
                adjustment_type = "Decrease"
            else:
                adjustment_type = None

            if previous_kg != 0:
                percentage_change = round(
                    ((current_kg - previous_kg) / previous_kg) * 100, 2
                )
            else:
                percentage_change = Decimal(0)

            validated_data.update(
                {
                    "rate_per_kg": round(current_kg, 2),
                    "diff_kg": diff_kg,
                    "diff_mt": diff_mt,
                    "final_rate_kg": final_rate_kg,
                    "final_rate_mt": final_rate_mt,
                    "adjustment_value": adjustment_value,
                    "adjustment_type": adjustment_type,
                    "percentage_change": percentage_change,
                }
            )
        else:
            if rate_per_mt:
                validated_data.update(
                    {
                        "rate_per_kg": round(rate_per_mt / Decimal(1000), 2),
                        "final_rate_kg": round(rate_per_mt / Decimal(1000), 2),
                        "final_rate_mt": round(rate_per_mt, 2),
                    }
                )

        return super().create(validated_data)

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
