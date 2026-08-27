from rest_framework import serializers
from die.models import Die, DieTool
from mechanical_test.models import MechanicalTest, MechanicalTestDetail
from common.serializers import BaseModelSerializer
from decimal import Decimal

from product.models import Alloy, Temper
from production.models import Production
from shift.models import ShiftMaster


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


class AlloySerializer(serializers.ModelSerializer):
    class Meta:
        model = Alloy
        fields = ["id", "alloy_code"]


class TemperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Temper
        fields = ["id", "temper_code_new"]


class MechanicalTestDetailSerializer(BaseModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta(BaseModelSerializer.Meta):
        model = MechanicalTestDetail
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "rack_no",
            "section_no",
            "production_no",
            "die_no",
            "cast_no",
            "cut_length_mm",
            "alloy",
            "temper",
            "pieces",
            "total_weight",
            "hardness_bhn",
            "conductivity_iacs",
            "qc_result",
            "remarks",
        ]

    def format_decimal(self, value):
        if value is None:
            return None
        value = Decimal(value)
        if value == value.to_integral():
            return int(value)
        return format(value, ".3f")

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.section_no:
            data["section_no"] = SectionSerializer(instance.section_no).data

        if instance.die_no:
            data["die_no"] = DieToolSerializer(instance.die_no).data

        if instance.alloy:
            data["alloy"] = AlloySerializer(instance.alloy).data

        if instance.temper:
            data["temper"] = TemperSerializer(instance.temper).data

        if instance.production_no:
            data["production_no"] = ProductionSerializer(instance.production_no).data

        if data.get("total_weight") is not None:
            data["total_weight"] = self.format_decimal(data["total_weight"])

        return data


class MechanicalTestSerializer(BaseModelSerializer):
    item_details = MechanicalTestDetailSerializer(
        source="test_details", many=True, required=False
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = MechanicalTest
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "qc_date",
            "source_type",
            "ageing_batch_no",
            "heat_treatment_no",
            "furnace_no",
            "shift",
            "shift_details",
            "start_time",
            "end_time",
            "item_details",
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

    def validate(self, attrs):
        source_type = attrs.get("source_type")
        if source_type is None and self.instance is not None:
            source_type = self.instance.source_type

        if source_type == "PRODUCTION":
            # No Ageing process → Heat No / Ageing batch must not apply
            attrs["heat_treatment_no"] = None
            attrs["ageing_batch_no"] = None
            if "furnace_no" in attrs and not attrs.get("furnace_no"):
                attrs["furnace_no"] = None
        elif source_type == "AGEING":
            ageing_batch = attrs.get("ageing_batch_no")
            if ageing_batch is None and self.instance is not None:
                ageing_batch = self.instance.ageing_batch_no
            if not ageing_batch:
                raise serializers.ValidationError(
                    {"ageing_batch_no": "Ageing Batch is required for Ageing source."}
                )
            heat_no = attrs.get("heat_treatment_no")
            if heat_no is None and self.instance is not None:
                heat_no = self.instance.heat_treatment_no
            if not heat_no:
                raise serializers.ValidationError(
                    {"heat_treatment_no": "Heat No is required for Ageing source."}
                )

        return attrs

    def to_representation(self, instance):
        response = super().to_representation(instance)

        if instance.ageing_batch_no:
            batch = instance.ageing_batch_no
            response["ageing_batch_no"] = {
                "id": batch.id,
                "batch_no": batch.batch_no,
                "cycle_time": batch.cycle_time,
                "temperature": batch.temperature,
                "soaking_time": (
                    batch.soaking_time.strftime("%H:%M:%S")
                    if batch.soaking_time
                    else None
                ),
                "furnace_no": batch.furnace_no,
                "heat_treatment_no": batch.heat_treatment_no,
            }

        return response

    def create(self, validated_data):
        details_data = validated_data.pop("test_details", [])
        shift = validated_data.pop("shift", None)
        created_by = validated_data.get("created_by")

        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift": "Selected shift is inactive"})

        test_detail = MechanicalTest(**validated_data)
        if shift:
            test_detail.capture_shift_snapshot(shift)
        test_detail.save()

        for detail_data in details_data:
            detail_data.pop("id", None)
            MechanicalTestDetail.objects.create(
                mechanical_test=test_detail, created_by=created_by, **detail_data
            )

        try:
            from workorder.process_tracking import advance_process

            user = (
                self.context.get("request").user
                if self.context.get("request")
                else created_by
            )
            for detail_data in details_data:
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
                    stage="MECHANICAL_TEST",
                    user=user,
                    remarks="Mechanical Test",
                )
        except Exception:
            pass

        return test_detail

    def update(self, instance, validated_data):
        details_data = validated_data.pop("test_details", None)
        updated_by = validated_data.get("updated_by")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if details_data is not None:
            existing_ids = set(
                instance.test_details.filter(deleted=False).values_list("id", flat=True)
            )
            incoming_ids = set()

            for detail_data in details_data:
                detail_id = detail_data.get("id")

                if detail_id is not None and detail_id in existing_ids:
                    incoming_ids.add(detail_id)
                    try:
                        detail_obj = MechanicalTestDetail.objects.get(
                            id=detail_id, mechanical_test=instance, deleted=False
                        )
                        for attr, value in detail_data.items():
                            if attr != "id":
                                setattr(detail_obj, attr, value)
                        detail_obj.updated_by = updated_by
                        detail_obj.save()
                    except MechanicalTestDetail.DoesNotExist:
                        pass
                else:
                    detail_data.pop("id", None)
                    new_detail = MechanicalTestDetail.objects.create(
                        mechanical_test=instance, created_by=updated_by, **detail_data
                    )
                    incoming_ids.add(new_detail.id)

            to_delete = existing_ids - incoming_ids
            if to_delete:
                from django.utils import timezone

                MechanicalTestDetail.objects.filter(id__in=to_delete).update(
                    deleted=True, deleted_by=updated_by, deleted_at=timezone.now()
                )

        return instance
