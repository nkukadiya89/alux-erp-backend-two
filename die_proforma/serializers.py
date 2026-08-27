from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone
from rest_framework import serializers

from common.serializers import BaseModelSerializer
from customer.serializers import CustomerSerializer
from die_proforma.models import DieProforma, DieProformaDetails
from utils.generate_number import get_financial_year


def generate_die_proforma_no():
    fy = get_financial_year()
    prefix = f"DPI/{fy}/"

    last = (
        DieProforma.objects.filter(proforma_no__startswith=prefix)
        .order_by("-proforma_no")
        .first()
    )

    if last and last.proforma_no:
        try:
            last_number = int(last.proforma_no.split("/")[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


class DieProformaDetailsSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DieProformaDetails
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "pieces",
            "description",
            "hsn",
            "quantity",
            "rate",
        ]


class DieProformaSerializer(BaseModelSerializer):
    die_proforma_details = serializers.ListField(required=False)

    class Meta(BaseModelSerializer.Meta):
        model = DieProforma
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer",
            "freight_charges",
            "advance_amount",
            "transport_charges",
            "insurance_charges",
            "other_charges",
            "proforma_date",
            "terms_and_condition",
            "purchase_order_date", 
            "remarks",
            "proforma_no",
            "purchase_order_no",
            "die_proforma_details",
        ]

    def get_instance(self, model, obj_id, error_message):
        if obj_id is not None:
            try:
                return model.objects.get(id=obj_id)
            except model.DoesNotExist:
                raise serializers.ValidationError(
                    {"success": False, "message": error_message}
                )
        return None

    def create(self, validated_data):
        details_data = validated_data.pop("die_proforma_details", None)
        validated_data["created_by"] = self.context["request"].user
        validated_data["proforma_no"] = generate_die_proforma_no()

        instance = DieProforma.objects.create(**validated_data)

        if details_data:
            for detail in details_data:
                detail["die_proforma"] = instance
                detail["created_by"] = self.context["request"].user
                detail["created_at"] = timezone.now()
                DieProformaDetails.objects.create(**detail)

        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        details_data = validated_data.pop("die_proforma_details", None)

        for field in [
            "customer", "freight_charges", "advance_amount",
            "transport_charges", "insurance_charges", "other_charges",
            "terms_and_condition", "remarks", "purchase_order_no", "purchase_order_date",
        ]:
            setattr(instance, field, validated_data.get(field, getattr(instance, field)))

        instance.updated_by = request.user
        instance.updated_at = timezone.now()

        detail_ids = []

        if details_data is not None:
            for detail in details_data:
                detail_id = detail.get("id")

                if detail_id:
                    try:
                        detail_obj = DieProformaDetails.objects.get(id=detail_id, die_proforma=instance)
                    except DieProformaDetails.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Die Proforma Detail not found."}
                        )
                    detail_obj.pieces = detail.get("pieces", detail_obj.pieces)
                    detail_obj.description = detail.get("description", detail_obj.description)
                    detail_obj.hsn = detail.get("hsn", detail_obj.hsn)
                    detail_obj.quantity = detail.get("quantity", detail_obj.quantity)
                    detail_obj.rate = detail.get("rate", detail_obj.rate)
                    detail_obj.updated_by = request.user
                    detail_obj.updated_at = timezone.now()
                    detail_obj.save()
                    detail_ids.append(detail_obj.id)
                else:
                    new_detail = DieProformaDetails.objects.create(
                        die_proforma=instance,
                        pieces=detail.get("pieces"),
                        description=detail.get("description"),
                        hsn=detail.get("hsn"),
                        quantity=detail.get("quantity"),
                        rate=detail.get("rate"),
                        created_by=request.user,
                        created_at=timezone.now(),
                        updated_by=request.user,
                        updated_at=timezone.now(),
                    )
                    detail_ids.append(new_detail.id)

            DieProformaDetails.objects.filter(die_proforma=instance).exclude(
                id__in=detail_ids
            ).update(deleted=True)

        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if instance.customer:
            ret["customer"] = CustomerSerializer(instance.customer).data

        customer = instance.customer
        applicable_gst = customer.applicable_gst if customer else None
        is_igst = applicable_gst and applicable_gst.upper() == "IGST"
        gst_type_name = applicable_gst or ""

        details_qs = DieProformaDetails.objects.filter(die_proforma=instance, deleted=False)

        total_basic_amount = Decimal("0.00")
        total_pieces = 0
        total_quantity = 0
        details_list = []

        for detail in details_qs:
            rate = Decimal(detail.rate or 0)
            quantity = Decimal(detail.quantity or 0)
            line_total = (rate * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            total_basic_amount += line_total
            total_pieces += int(detail.pieces or 0)
            total_quantity += int(detail.quantity or 0)

            detail_data = DieProformaDetailsSerializer(detail, context=self.context).data
            detail_data["amount"] = format(line_total, ".2f")
            details_list.append(detail_data)

        ret["die_proforma_details"] = details_list

        freight_charges = Decimal(instance.freight_charges or 0).quantize(Decimal("0.01"))
        transport_charges = Decimal(instance.transport_charges or 0).quantize(Decimal("0.01"))
        insurance_charges = Decimal(instance.insurance_charges or 0).quantize(Decimal("0.01"))
        other_charges = Decimal(instance.other_charges or 0).quantize(Decimal("0.01"))
        advance_amount = Decimal(instance.advance_amount or 0)

        taxable_value = (
            total_basic_amount
            + freight_charges
            + transport_charges
            + insurance_charges
            + other_charges
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        gst_rate = Decimal("18") / Decimal("100")

        if is_igst:
            igst = (taxable_value * gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
        else:
            cgst = (taxable_value * gst_rate / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sgst = (taxable_value * gst_rate / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            igst = Decimal("0.00")

        total_gst = igst + cgst + sgst
        total_payable = (taxable_value + total_gst).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rounded_total = total_payable.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        round_off = (rounded_total - total_payable).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        final_amount = (rounded_total - abs(advance_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        ret["summary"] = {
            "gst_type": gst_type_name,
            "freight_charges": format(freight_charges, ".2f"),
            "transport_charges": format(transport_charges, ".2f"),
            "insurance_charges": format(insurance_charges, ".2f"),
            "other_charges": format(other_charges, ".2f"),
            "igst": format(igst, ".2f"),
            "cgst": format(cgst, ".2f"),
            "sgst": format(sgst, ".2f"),
            "total_basic_amount": format(total_basic_amount, ".2f"),
            "taxable_value": format(taxable_value, ".2f"),
            "total_gst": format(total_gst, ".2f"),
            "advance_amount": format(advance_amount, ".2f"),
            "round_off": format(round_off, ".2f"),
            "total_payable_amount": format(total_payable, ".2f"),
            "final_amount": format(rounded_total, ".2f"),
            "amount_after_advance": format(final_amount, ".2f"),
            "total_pieces": total_pieces,
            "total_quantity": total_quantity,
        }

        return ret
