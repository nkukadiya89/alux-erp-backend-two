from decimal import Decimal

from rest_framework import serializers

from common.models import JobWorkType, Plant
from common.serializers import BaseModelSerializer
from customer.models import Customer
from jobwork_invoice.models import JobworkInvoice
from production.models import Production
from return_qc.models import ReturnQC, ReturnQCLine
from shift.models import ShiftMaster
from utils.generate_number import generate_return_qc_no


VENDOR_CUSTOMER_QS = Customer.objects.filter(
    deleted=False, company_type__in=["vendor", "customer_vendor"]
)


class ReturnQCLineSerializer(BaseModelSerializer):
    id = serializers.IntegerField(required=False)
    production = serializers.PrimaryKeyRelatedField(
        queryset=Production.objects.filter(deleted=False)
    )

    class Meta(BaseModelSerializer.Meta):
        model = ReturnQCLine
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "production",
            "workorder",
            "workorder_detail",
            "section_no",
            "die_no",
            "alloy",
            "temper",
            "pieces_sent",
            "pieces_received",
            "pieces_accepted",
            "pieces_rejected",
            "cut_length_mm",
            "weight_received",
            "qc_result",
            "defect_type",
            "remarks",
        ]
        read_only_fields = ["workorder", "workorder_detail"]

    def format_decimal(self, value):
        if value is None:
            return None
        value = Decimal(value)
        if value == value.to_integral():
            return int(value)
        return format(value, ".3f")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.production:
            data["production"] = {
                "id": instance.production.id,
                "production_no": instance.production.production_no,
            }
        if instance.workorder:
            data["workorder"] = {
                "id": instance.workorder.id,
                "order_no": instance.workorder.order_no,
            }
        if instance.workorder_detail:
            data["workorder_detail"] = {"id": instance.workorder_detail.id}
        if instance.section_no:
            data["section_no"] = {
                "id": instance.section_no.id,
                "die_number": instance.section_no.die_number,
            }
        if instance.die_no:
            data["die_no"] = {
                "id": instance.die_no.id,
                "tool_number": instance.die_no.tool_number,
            }
        if instance.alloy:
            data["alloy"] = {
                "id": instance.alloy.id,
                "alloy_code": instance.alloy.alloy_code,
            }
        if instance.temper:
            data["temper"] = {
                "id": instance.temper.id,
                "temper_code_new": instance.temper.temper_code_new,
            }
        if data.get("weight_received") is not None:
            data["weight_received"] = self.format_decimal(data["weight_received"])
        return data


class ReturnQCSerializer(BaseModelSerializer):
    item_details = ReturnQCLineSerializer(source="qc_lines", many=True, required=True)
    vendor = serializers.PrimaryKeyRelatedField(queryset=VENDOR_CUSTOMER_QS)
    jobwork_invoice = serializers.PrimaryKeyRelatedField(
        queryset=JobworkInvoice.objects.filter(deleted=False),
        required=False,
        allow_null=True,
    )
    jobwork_type = serializers.PrimaryKeyRelatedField(
        queryset=JobWorkType.objects.all(),
        required=False,
        allow_null=True,
    )
    plant = serializers.PrimaryKeyRelatedField(
        queryset=Plant.objects.filter(deleted=False),
        required=False,
        allow_null=True,
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    shift_details = serializers.SerializerMethodField(read_only=True)
    inspection_no = serializers.CharField(required=False, allow_blank=True)

    class Meta(BaseModelSerializer.Meta):
        model = ReturnQC
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "inspection_no",
            "inspection_date",
            "vendor",
            "jobwork_invoice",
            "jobwork_type",
            "plant",
            "vehicle_no",
            "gate_entry_ref",
            "overall_result",
            "remarks",
            "attachment",
            "shift",
            "shift_details",
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
        lines = attrs.get("qc_lines")
        if lines is not None and len(lines) == 0:
            raise serializers.ValidationError(
                {"item_details": "At least one production line is required."}
            )
        shift = attrs.get("shift")
        if shift and not shift.is_active:
            raise serializers.ValidationError({"shift": "Selected shift is inactive"})

        if lines:
            from workorder.process_tracking import resolve_jobwork_stage_codes

            for idx, line_data in enumerate(lines):
                production = line_data.get("production")
                if not production:
                    continue
                planning = getattr(production, "planning", None)
                wod = planning.workorder_detail if planning else None
                if not wod:
                    raise serializers.ValidationError(
                        {
                            "item_details": (
                                f"Line {idx + 1}: production has no work order detail."
                            )
                        }
                    )
                stages = resolve_jobwork_stage_codes(wod)
                if "JW_RETURN_QC" not in stages:
                    raise serializers.ValidationError(
                        {
                            "item_details": (
                                f"Line {idx + 1}: Return QC applies only on the vendor "
                                "jobwork path (after Vendor Out / Jobwork Invoice)."
                            )
                        }
                    )
        return attrs

    def _enrich_line_from_production(self, line_data):
        production = line_data.get("production")
        if not production:
            return line_data
        planning = getattr(production, "planning", None)
        wod = planning.workorder_detail if planning else None
        line_data.setdefault("workorder", production.workorder)
        if wod:
            line_data.setdefault("workorder_detail", wod)
        if not line_data.get("section_no"):
            line_data["section_no"] = production.die_profile
        if not line_data.get("die_no"):
            line_data["die_no"] = production.die_tool
        if not line_data.get("alloy"):
            line_data["alloy"] = production.alloy
        if not line_data.get("temper"):
            line_data["temper"] = production.temper
        return line_data

    def _advance_return_qc_process(self, lines_data, user, inspection_no):
        try:
            from workorder.process_tracking import advance_process

            for line_data in lines_data:
                production = line_data.get("production")
                if not production:
                    continue
                planning = getattr(production, "planning", None)
                wod = planning.workorder_detail if planning else None
                if not wod:
                    continue
                advance_process(
                    workorder_detail=wod,
                    planning=planning,
                    stage="JW_RETURN_QC",
                    user=user,
                    remarks=f"Return QC {inspection_no}",
                )
        except Exception:
            pass

    def create(self, validated_data):
        lines_data = validated_data.pop("qc_lines", [])
        shift = validated_data.pop("shift", None)
        created_by = validated_data.get("created_by")

        if not validated_data.get("inspection_no"):
            validated_data["inspection_no"] = generate_return_qc_no()

        inspection = ReturnQC(**validated_data)
        if shift:
            inspection.capture_shift_snapshot(shift)
        inspection.save()

        enriched_lines = []
        for line_data in lines_data:
            line_data = dict(line_data)
            line_data.pop("id", None)
            line_data = self._enrich_line_from_production(line_data)
            ReturnQCLine.objects.create(
                return_qc=inspection, created_by=created_by, **line_data
            )
            enriched_lines.append(line_data)

        user = (
            self.context.get("request").user
            if self.context.get("request")
            else created_by
        )
        self._advance_return_qc_process(enriched_lines, user, inspection.inspection_no)
        return inspection

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("qc_lines", None)
        shift = validated_data.pop("shift", None)
        updated_by = validated_data.get("updated_by")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if shift:
            instance.capture_shift_snapshot(shift)
        instance.save()

        if lines_data is not None:
            keep_ids = []
            for line_data in lines_data:
                line_data = dict(line_data)
                line_id = line_data.pop("id", None)
                line_data = self._enrich_line_from_production(line_data)
                if line_id:
                    line = ReturnQCLine.objects.filter(
                        id=line_id, return_qc=instance, deleted=False
                    ).first()
                    if line:
                        for attr, value in line_data.items():
                            setattr(line, attr, value)
                        line.updated_by = updated_by
                        line.save()
                        keep_ids.append(line.id)
                        continue
                created = ReturnQCLine.objects.create(
                    return_qc=instance,
                    created_by=updated_by or instance.created_by,
                    **line_data,
                )
                keep_ids.append(created.id)
            ReturnQCLine.objects.filter(return_qc=instance, deleted=False).exclude(
                id__in=keep_ids
            ).update(deleted=True)
        return instance

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if instance.vendor:
            response["vendor"] = {
                "id": instance.vendor.id,
                "customer_name": instance.vendor.customer_name,
                "code": instance.vendor.code,
                "company_type": instance.vendor.company_type,
                "vendor_registered_name": instance.vendor.customer_name,
            }
        if instance.jobwork_invoice:
            response["jobwork_invoice"] = {
                "id": instance.jobwork_invoice.id,
                "challan_no": instance.jobwork_invoice.challan_no,
            }
        if instance.jobwork_type:
            response["jobwork_type"] = {
                "id": instance.jobwork_type.id,
                "name": instance.jobwork_type.name,
            }
        if instance.plant:
            response["plant"] = {
                "id": str(instance.plant.id),
                "plant_name": instance.plant.plant_name,
                "plant_code": instance.plant.plant_code,
            }
        response["item_details"] = ReturnQCLineSerializer(
            instance.qc_lines.filter(deleted=False), many=True
        ).data
        return response
