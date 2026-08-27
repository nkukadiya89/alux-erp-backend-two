from rest_framework import serializers
from django.db import transaction

from inquiry.serializers import AlloySerializer, TemperSerializer
from online_inspection.models import OnlineInspection, OnlineInspectionDetail
from die.models import Die
from production.models import Production
from common.serializers import BaseModelSerializer


class OnlineInspectionDetailSerializer(serializers.ModelSerializer):
    production_no = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    section_no = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    production_data = serializers.SerializerMethodField(read_only=True)
    section_data = serializers.SerializerMethodField(read_only=True)
    alloy_detail = AlloySerializer(source="alloy", read_only=True)
    temper_detail = TemperSerializer(source="temper", read_only=True)

    class Meta:
        model = OnlineInspectionDetail
        fields = [
            "id",
            "production_no",
            "production_data",
            "section_no",
            "section_data",
            "cut_length_mm",
            "alloy",
            "alloy_detail",
            "temper",
            "temper_detail",
            "planned_pieces",
            "act_inspected_pieces",
            "bend_twist",
            "blister",
            "scoring",
            "scratch",
            "damage",
            "joint",
            "dimension",
            "concave",
            "hardness",
            "line",
            "section_cut",
            "core_defect",
            "chattering",
            "roughness_pickup",
            "rack_no",
            "remark",
        ]

    def get_production_data(self, obj):
        if obj.production:
            return {
                "id": obj.production.id,
                "production_no": obj.production.production_no,
            }
        return None

    def get_section_data(self, obj):
        if obj.section:
            return {"id": obj.section.id, "die_number": obj.section.die_number}
        return None

    def validate(self, attrs):
        production_no = attrs.pop("production_no", None)
        section_no = attrs.pop("section_no", None)

        if production_no:
            try:
                attrs["production"] = Production.objects.get(id=production_no)
            except Production.DoesNotExist:
                raise serializers.ValidationError(
                    {"production_no": "Production not found"}
                )

        if section_no:
            try:
                attrs["section"] = Die.objects.get(id=section_no)
            except Die.DoesNotExist:
                raise serializers.ValidationError({"section_no": "Section not found"})

        planned = attrs.get("planned_pieces")
        inspected = attrs.get("act_inspected_pieces")

        if planned is not None and inspected is not None:
            if inspected > planned:
                raise serializers.ValidationError(
                    {
                        "act_inspected_pieces": "Inspected pieces cannot exceed planned pieces"
                    }
                )

        return attrs


class OnlineInspectionSerializer(BaseModelSerializer):
    qc_rack_details = OnlineInspectionDetailSerializer(many=True)
    press_name = serializers.CharField(source="press.name", read_only=True)
    shift_details = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = OnlineInspection
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "inspection_date",
            "shift",
            "shift_details",
            "press",
            "press_name",
            "qc_rack_details",
        ]
        read_only_fields = [
            "shift_name_snapshot",
            "shift_start_snapshot",
            "shift_end_snapshot",
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

    def validate_press(self, value):
        if value.deleted:
            raise serializers.ValidationError("Selected press is deleted")
        return value

    def validate_qc_rack_details(self, value):
        if not value:
            raise serializers.ValidationError("At least one QC rack detail is required")
        return value

    @transaction.atomic
    def create(self, validated_data):
        qc_rack_details = validated_data.pop("qc_rack_details")
        shift = validated_data.pop("shift", None)

        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift": "Selected shift is inactive"})

        inspection = OnlineInspection(**validated_data)
        if shift:
            inspection.capture_shift_snapshot(shift)
        inspection.save()

        for detail_data in qc_rack_details:
            OnlineInspectionDetail.objects.create(
                online_inspection=inspection, **detail_data
            )

        try:
            from workorder.process_tracking import advance_process

            user = (
                self.context.get("request").user
                if self.context.get("request")
                else None
            )
            for detail_data in qc_rack_details:
                production = detail_data.get("production")
                if not production:
                    continue
                planning = getattr(production, "planning", None)
                wod = planning.workorder_detail if planning else None
                if not wod:
                    continue
                advance_process(
                    workorder_detail=wod,
                    planning=planning,
                    stage="ONLINE_INSPECTION",
                    user=user,
                    remarks="Online Inspection",
                )
        except Exception:
            pass

        return inspection

    @transaction.atomic
    def update(self, instance, validated_data):
        qc_rack_details = validated_data.pop("qc_rack_details", None)
        shift = validated_data.pop("shift", None)

        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift": "Selected shift is inactive"})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if shift:
            instance.capture_shift_snapshot(shift)

        instance.save()

        if qc_rack_details is not None:
            instance.qc_rack_details.all().delete()
            for detail_data in qc_rack_details:
                OnlineInspectionDetail.objects.create(
                    online_inspection=instance, **detail_data
                )

        return instance
