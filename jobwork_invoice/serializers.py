from decimal import Decimal

from rest_framework import serializers

from common.models import JobWorkType, Plant
from common.serializers import BaseModelSerializer
from customer.models import Customer
from jobwork_invoice.models import JobworkInvoice, JobworkInvoiceLine
from production.models import Production
from shift.models import ShiftMaster
from utils.generate_number import generate_jobwork_challan_no


VENDOR_CUSTOMER_QS = Customer.objects.filter(
    deleted=False, company_type__in=["vendor", "customer_vendor"]
)


class JobworkInvoiceLineSerializer(BaseModelSerializer):
    id = serializers.IntegerField(required=False)
    production = serializers.PrimaryKeyRelatedField(
        queryset=Production.objects.filter(deleted=False)
    )

    class Meta(BaseModelSerializer.Meta):
        model = JobworkInvoiceLine
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "production",
            "workorder",
            "workorder_detail",
            "section_no",
            "die_no",
            "alloy",
            "temper",
            "pieces",
            "cut_length_mm",
            "total_weight",
            "rate",
            "amount",
            "jobwork_description",
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
        if data.get("total_weight") is not None:
            data["total_weight"] = self.format_decimal(data["total_weight"])
        return data


class JobworkInvoiceSerializer(BaseModelSerializer):
    item_details = JobworkInvoiceLineSerializer(
        source="invoice_lines", many=True, required=True
    )
    vendor = serializers.PrimaryKeyRelatedField(queryset=VENDOR_CUSTOMER_QS)
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
    challan_no = serializers.CharField(required=False, allow_blank=True)

    class Meta(BaseModelSerializer.Meta):
        model = JobworkInvoice
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "challan_no",
            "challan_date",
            "vendor",
            "jobwork_type",
            "vendor_invoice_no",
            "vendor_invoice_date",
            "vehicle_no",
            "gate_pass_ref",
            "plant",
            "taxable_amount",
            "tax_amount",
            "total_amount",
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
        lines = attrs.get("invoice_lines")
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
                                f"Line {idx + 1}: production has no work order detail "
                                "for jobwork linking."
                            )
                        }
                    )
                stages = resolve_jobwork_stage_codes(wod)
                if "JW_INVOICE_LINKED" not in stages:
                    raise serializers.ValidationError(
                        {
                            "item_details": (
                                f"Line {idx + 1}: this work order item is on an in-house "
                                "jobwork path (e.g. Cutting only). Jobwork Challan / "
                                "vendor invoice applies only when vendor processes "
                                "(Machining, Anodising, Out Source, etc.) are selected."
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

    def _advance_jobwork_process(self, lines_data, user, challan_no):
        """
        Completing JW_INVOICE_LINKED also completes prior applicable stages
        (e.g. JW_MACHINING, JW_VENDOR_OUT) via advance_process upto-semantics.
        """
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
                    stage="JW_INVOICE_LINKED",
                    user=user,
                    remarks=f"Jobwork Challan {challan_no}",
                )
        except Exception:
            pass

    def create(self, validated_data):
        lines_data = validated_data.pop("invoice_lines", [])
        shift = validated_data.pop("shift", None)
        created_by = validated_data.get("created_by")

        if not validated_data.get("challan_no"):
            validated_data["challan_no"] = generate_jobwork_challan_no()

        invoice = JobworkInvoice(**validated_data)
        if shift:
            invoice.capture_shift_snapshot(shift)
        invoice.save()

        enriched_lines = []
        for line_data in lines_data:
            line_data = dict(line_data)
            line_data.pop("id", None)
            line_data = self._enrich_line_from_production(line_data)
            JobworkInvoiceLine.objects.create(
                jobwork_invoice=invoice, created_by=created_by, **line_data
            )
            enriched_lines.append(line_data)

        user = (
            self.context.get("request").user
            if self.context.get("request")
            else created_by
        )
        self._advance_jobwork_process(enriched_lines, user, invoice.challan_no)
        return invoice

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("invoice_lines", None)
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
                    line = JobworkInvoiceLine.objects.filter(
                        id=line_id, jobwork_invoice=instance, deleted=False
                    ).first()
                    if line:
                        for attr, value in line_data.items():
                            setattr(line, attr, value)
                        line.updated_by = updated_by
                        line.save()
                        keep_ids.append(line.id)
                        continue
                created = JobworkInvoiceLine.objects.create(
                    jobwork_invoice=instance,
                    created_by=updated_by or instance.created_by,
                    **line_data,
                )
                keep_ids.append(created.id)

            JobworkInvoiceLine.objects.filter(
                jobwork_invoice=instance, deleted=False
            ).exclude(id__in=keep_ids).update(deleted=True)

        return instance

    def to_representation(self, instance):
        response = super().to_representation(instance)

        if instance.vendor:
            response["vendor"] = {
                "id": instance.vendor.id,
                "customer_name": instance.vendor.customer_name,
                "code": instance.vendor.code,
                "company_type": instance.vendor.company_type,
                # Aliases for UI compatibility with older vendor field names
                "vendor_registered_name": instance.vendor.customer_name,
                "vendor_trade_name": instance.vendor.customer_name,
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

        response["item_details"] = JobworkInvoiceLineSerializer(
            instance.invoice_lines.filter(deleted=False), many=True
        ).data
        return response
