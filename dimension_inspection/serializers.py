from rest_framework import serializers
from dimension_inspection.models import DimensionInspection, DimensionInspectionDetail
from common.serializers import BaseModelSerializer
from shift.models import ShiftMaster
from decimal import Decimal
from django.db import transaction


class DimensionInspectionDetailSerializer(BaseModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta(BaseModelSerializer.Meta):
        model = DimensionInspectionDetail
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "nominal",
            "tolerance",
            "before_cav_1",
            "before_cav_2",
            "before_cav_3",
            "before_cav_4",
            "before_cav_5",
            "before_cav_6",
            "before_cav_7",
            "before_cav_8",
            "before_cav_9",
            "before_cav_10",
            "after_cav_1",
            "after_cav_2",
            "after_cav_3",
            "after_cav_4",
            "after_cav_5",
            "after_cav_6",
            "after_cav_7",
            "after_cav_8",
            "after_cav_9",
            "after_cav_10",
        ]

    def format_decimal(self, value):
        if value is None:
            return None

        value = Decimal(value)

        if value == value.to_integral():
            return int(value)

        return format(value, ".2f")

    def to_representation(self, instance):
        data = super().to_representation(instance)

        decimal_fields = [
            "nominal",
            "tolerance",
            "before_cav_1",
            "before_cav_2",
            "before_cav_3",
            "before_cav_4",
            "before_cav_5",
            "before_cav_6",
            "before_cav_7",
            "before_cav_8",
            "before_cav_9",
            "before_cav_10",
            "after_cav_1",
            "after_cav_2",
            "after_cav_3",
            "after_cav_4",
            "after_cav_5",
            "after_cav_6",
            "after_cav_7",
            "after_cav_8",
            "after_cav_9",
            "after_cav_10",
        ]

        for field in decimal_fields:
            value = data.get(field)
            if value is not None:
                data[field] = self.format_decimal(value)

        return data


class DimensionInspectionSerializer(BaseModelSerializer):
    dimension_inspection_details = DimensionInspectionDetailSerializer(
        many=True, required=False
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False
    )
    shift_details = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = DimensionInspection
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "inspection_date",
            "production",
            "workorder",
            "customer",
            "cut_length",
            "container_temp",
            "die_no",
            "quenching_type",
            "head_end_scrap",
            "tail_end_scrap",
            "total_scrap",
            "section",
            "billet_length",
            "wt_mtr",
            "front_end_scrap",
            "back_end_scrap",
            "butt_end",
            "billet_cast_no",
            "die_unloading_reason",
            "die_unloading_other",
            "die_temp",
            "extrusion_speed",
            "planned_billet",
            "cooling_rate",
            "extruded_billet",
            "pullar_force_kgs",
            "billet_temp",
            "section_exit_temp",
            "sample_checked",
            "remarks",
            "alloy",
            "temper",
            "press",
            "shift",
            "shift_details",
            "dimension_inspection_details",
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

    def format_decimal(self, value):
        if value is None:
            return None

        value = Decimal(value)

        if value == value.to_integral():
            return int(value)

        return format(value, ".2f")

    def to_representation(self, instance):
        response = super().to_representation(instance)

        if instance.production:
            response["production"] = {
                "id": instance.production.id,
                "production_no": (
                    instance.production.production_no
                    if hasattr(instance.production, "production_no")
                    else None
                ),
            }

        if instance.workorder:
            response["workorder"] = {
                "id": instance.workorder.id,
                "work_order_no": (
                    instance.workorder.order_no
                    if hasattr(instance.workorder, "order_no")
                    else None
                ),
            }

        if instance.customer:
            response["customer"] = {
                "id": instance.customer.id,
                "customer_name": instance.customer.customer_name,
                "code": instance.customer.code,
            }

        if instance.section:
            response["section"] = {
                "id": instance.section.id,
                "die_number": instance.section.die_number,
            }

        if instance.alloy:
            response["alloy"] = {
                "id": instance.alloy.id,
                "alloy_code": instance.alloy.alloy_code,
                "standard_name": (
                    instance.alloy.standard.name
                    if instance.alloy.standard
                    else None
                ),
            }

        if instance.temper:
            response["temper"] = {
                "id": instance.temper.id,
                "temper_code_new": instance.temper.temper_code_new,
                "standard_name": (
                    instance.temper.standard.name
                    if instance.temper.standard
                    else None
                ),
            }

        if instance.press:
            response["press"] = {"id": instance.press.id, "name": instance.press.name}

        if instance.die_no:
            response["die_no"] = {
                "id": instance.die_no.id,
                "tool_number": instance.die_no.tool_number,
                "die_number": instance.die_no.die.die_number,
            }

        decimal_fields = [
            "container_temp",
            "wt_mtr",
            "front_end_scrap",
            "back_end_scrap",
            "head_end_scrap",
            "tail_end_scrap",
            "total_scrap",
            "butt_end",
            "extrusion_speed",
            "cooling_rate",
            "pullar_force_kgs",
            "billet_temp",
            "section_exit_temp",
            "die_temp",
        ]

        for field in decimal_fields:
            value = response.get(field)
            if value is not None:
                response[field] = self.format_decimal(value)

        return response

    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop("dimension_inspection_details", [])
        shift = validated_data.pop("shift", None)

        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift" " Selected shift is inactive"})

        inspection = DimensionInspection(**validated_data)
        if shift:
            inspection.capture_shift_snapshot(shift)
        inspection.save()

        for detail_data in details_data:
            DimensionInspectionDetail.objects.create(
                dimension_inspection=inspection, **detail_data
            )

        try:
            from workorder.process_tracking import advance_process

            user = (
                self.context.get("request").user
                if self.context.get("request")
                else None
            )
            production = validated_data.get("production") or inspection.production
            planning = getattr(production, "planning", None) if production else None
            wod = None
            if planning:
                wod = planning.workorder_detail
            if not wod and inspection.workorder_id:
                # Fall back: first open detail on WO (dimension may not pin item)
                wod = inspection.workorder.workorder_detail_workorder.filter(
                    deleted=False
                ).first()
            if wod:
                advance_process(
                    workorder_detail=wod,
                    planning=planning,
                    stage="DIMENSION_INSPECTION",
                    user=user,
                    remarks="Dimension Inspection",
                )
        except Exception:
            pass

        return inspection

    @transaction.atomic
    def update(self, instance, validated_data):
        details_data = validated_data.pop("dimension_inspection_details", None)

        updated_by = validated_data.get("updated_by")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if details_data is not None:
            existing_ids = set(
                instance.dimension_inspection_details.filter(deleted=False).values_list(
                    "id", flat=True
                )
            )
            incoming_ids = set()

            for detail_data in details_data:
                detail_id = detail_data.get("id")

                if detail_id is not None and detail_id in existing_ids:
                    incoming_ids.add(detail_id)
                    try:
                        detail_obj = DimensionInspectionDetail.objects.get(
                            id=detail_id, dimension_inspection=instance, deleted=False
                        )
                        for attr, value in detail_data.items():
                            if attr != "id":
                                setattr(detail_obj, attr, value)
                        detail_obj.updated_by = updated_by
                        detail_obj.save()
                    except DimensionInspectionDetail.DoesNotExist:
                        pass
                else:
                    detail_data.pop("id", None)
                    new_detail = DimensionInspectionDetail.objects.create(
                        dimension_inspection=instance,
                        created_by=updated_by,
                        **detail_data
                    )
                    incoming_ids.add(new_detail.id)

            to_delete = existing_ids - incoming_ids
            if to_delete:
                from django.utils import timezone

                DimensionInspectionDetail.objects.filter(id__in=to_delete).update(
                    deleted=True, deleted_by=updated_by, deleted_at=timezone.now()
                )

        return instance
