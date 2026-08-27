from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone
from rest_framework import serializers

from common.models import GstType, JobWorkType, PackingMode
from common.serializers import (
    BaseModelSerializer,
    JobWorkSerializer,
    PackingModeSortSerializer,
)
from customer.serializers import CustomerSerializer
from die.models import Die
from die.sort_serializers import DieSortSerializers
from product.models import Alloy, Temper
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from proforma.models import Proforma, ProformaDetails
from utils.generate_number import generate_proforma_no
from workorder.models import WorkOrderDetail
from django.db.models import Sum


class ProformaDetailsSerializers(BaseModelSerializer):
    jobworks = serializers.PrimaryKeyRelatedField(
        queryset=JobWorkType.objects.all(), many=True, required=False
    )
    jobwork_details = JobWorkSerializer(source="jobworks", many=True, read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = ProformaDetails
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "profile_no",
            "alloy",
            "temper",
            "description",
            "customer_reference_no",
            "out_source",
            "out_source",
            "cutting",
            "machining",
            "deburring",
            "cutting_price",
            "machining_price",
            "deburring_price",
            "anodising",
            "powder_coating",
            "pvdf",
            "anodising_price",
            "conversion",
            "anodising_description",
            "powder_coating_price",
            "powder_coating_description",
            "pvdf_price",
            "pvdf_description",
            "laser_marking_description",
            "laser_marking_price",
            "jobworks",
            "jobwork_details",
            "length",
            "pieces",
            "net_weight",
            "nalco_rate",
            "packed_weight",
            "dispatch_qty",
        ]

    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)
        return validated_data

    def create(self, validated_data):
        jobwork_names = validated_data.pop("jobwork", [])
        instance = super().create(validated_data)
        if jobwork_names:
            jobworks = JobWorkType.objects.filter(name__in=jobwork_names)
            instance.jobworks.set(jobworks)
        return instance

    def update(self, instance, validated_data):
        jobwork_names = validated_data.pop("jobwork", None)
        instance = super().update(instance, validated_data)
        if jobwork_names is not None:
            jobworks = JobWorkType.objects.filter(name__in=jobwork_names)
            instance.jobworks.set(jobworks)
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if "profile_no" in ret:
            ret["profile_no"] = DieSortSerializers(instance.profile_no).data

        if "alloy" in ret:
            ret["alloy"] = AlloySortSerializers(instance.alloy).data

        if "temper" in ret:
            ret["temper"] = TemperSortSerializers(instance.temper).data

        if ret.get("length") is not None:
            ret["length"] = int(float(ret["length"]))

        return ret


class ProformaSerializers(BaseModelSerializer):
    proforma_details = serializers.ListField(required=False)
    packing_mode = serializers.PrimaryKeyRelatedField(
        queryset=PackingMode.objects.filter(deleted=False), many=True, required=False
    )
    packing_mode_details = PackingModeSortSerializer(
        source="packing_mode", many=True, read_only=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = Proforma
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "workorder",
            "workorder_no",
            "customer",
            "packing_mode",
            "packing_mode_details",
            "proforma_date",
            "freight_charges",
            "type",
            "advance_amount",
            "transport_charges",
            "insurance_charges",
            "other_charges",
            "proforma_date",
            "terms_and_condition",
            "delivery_schedule",
            "weight_range",
            "remarks",
            "proforma_no",
            "proforma_details",
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
        proforma_details_data = validated_data.pop("proforma_details", None)
        packing_mode_ids = validated_data.pop("packing_mode", [])
        validated_data["created_by"] = self.context["request"].user
        validated_data["proforma_no"] = generate_proforma_no(self)

        proforma_instance = Proforma.objects.create(**validated_data)

        if packing_mode_ids:
            proforma_instance.packing_mode.set(packing_mode_ids)

        if proforma_details_data is not None:
            for proforma_detail_data in proforma_details_data:
                jobwork_ids = proforma_detail_data.pop("jobworks", [])
                jobwork_instances = []
                if isinstance(jobwork_ids, list) and jobwork_ids:
                    jobwork_instances = list(
                        JobWorkType.objects.filter(id__in=jobwork_ids)
                    )

                profile_no_id = proforma_detail_data.pop("profile_no", None)
                if profile_no_id is not None:
                    try:
                        die_instance = Die.objects.get(id=profile_no_id)
                        proforma_detail_data["profile_no"] = die_instance
                    except Die.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Die instance not found."}
                        )

                alloy_id = proforma_detail_data.pop("alloy", None)
                if alloy_id is not None:
                    try:
                        alloy_instance = Alloy.objects.get(id=alloy_id)
                        proforma_detail_data["alloy"] = alloy_instance
                    except Alloy.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Alloy instance not found."}
                        )

                temper_id = proforma_detail_data.pop("temper", None)
                if temper_id is not None:
                    try:
                        temper_instance = Temper.objects.get(id=temper_id)
                        proforma_detail_data["temper"] = temper_instance
                    except Temper.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Temper instance not found."}
                        )

                proforma_detail_data["proforma"] = proforma_instance
                proforma_detail_data["created_by"] = self.context["request"].user
                proforma_detail_data["created_at"] = timezone.now()
                proforma_detail_instance = ProformaDetails.objects.create(
                    **proforma_detail_data
                )

                if jobwork_instances:
                    proforma_detail_instance.jobworks.set(jobwork_instances)

        return proforma_instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        packing_mode_ids = validated_data.pop("packing_mode", None)
        if packing_mode_ids is not None:
            instance.packing_mode.set(packing_mode_ids)

        for field in [
            "workorder",
            "workorder_no",
            "customer",
            "proforma_date",
            "freight_charges",
            "transport_charges",
            "insurance_charges",
            "other_charges",
            "advance_amount",
            "terms_and_condition",
            "delivery_schedule",
            "weight_range",
            "remarks",
            "proforma_no",
        ]:
            setattr(
                instance, field, validated_data.get(field, getattr(instance, field))
            )

        instance.updated_by = request.user
        instance.updated_at = timezone.now()

        proforma_details_data = validated_data.pop("proforma_details", None)
        proforma_details_ids = []

        if proforma_details_data is not None:
            for proforma_detail_data in proforma_details_data:
                proforma_detail_id = proforma_detail_data.get("id")

                profile_no_instance = self.get_instance(
                    Die, proforma_detail_data.pop("profile_no", None), "Die Not Found"
                )
                alloy_instance = self.get_instance(
                    Alloy, proforma_detail_data.pop("alloy", None), "Alloy Not Found"
                )
                temper_instance = self.get_instance(
                    Temper, proforma_detail_data.pop("temper", None), "Temper Not Found"
                )

                if proforma_detail_id:
                    try:
                        proforma_details_instance = ProformaDetails.objects.get(
                            id=proforma_detail_id, proforma=instance
                        )
                    except ProformaDetails.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Proforma Details Not Found."}
                        )

                    proforma_details_instance.customer_reference_no = (
                        proforma_detail_data.get(
                            "customer_reference_no",
                            proforma_details_instance.customer_reference_no,
                        )
                    )
                    proforma_details_instance.temper = temper_instance
                    proforma_details_instance.alloy = alloy_instance
                    proforma_details_instance.profile_no = profile_no_instance

                    proforma_details_instance.out_source = proforma_detail_data.get(
                        "out_source", proforma_details_instance.out_source
                    )

                    proforma_details_instance.cutting = proforma_detail_data.get(
                        "cutting"
                    )
                    proforma_details_instance.machining = proforma_detail_data.get(
                        "machining"
                    )
                    proforma_details_instance.deburring = proforma_detail_data.get(
                        "deburring"
                    )
                    proforma_details_instance.cutting_price = proforma_detail_data.get(
                        "cutting_price"
                    )
                    proforma_details_instance.machining_price = (
                        proforma_detail_data.get("machining_price")
                    )
                    proforma_details_instance.deburring_price = (
                        proforma_detail_data.get("deburring_price")
                    )
                    proforma_details_instance.anodising = proforma_detail_data.get(
                        "anodising"
                    )
                    proforma_details_instance.powder_coating = proforma_detail_data.get(
                        "powder_coating"
                    )
                    proforma_details_instance.pvdf = proforma_detail_data.get("pvdf")
                    proforma_details_instance.anodising_description = (
                        proforma_detail_data.get("anodising_description")
                    )
                    proforma_details_instance.anodising_price = (
                        proforma_detail_data.get("anodising_price")
                    )
                    proforma_details_instance.powder_coating_description = (
                        proforma_detail_data.get("powder_coating_description")
                    )
                    proforma_details_instance.powder_coating_price = (
                        proforma_detail_data.get("powder_coating_price")
                    )
                    proforma_details_instance.pvdf_description = (
                        proforma_detail_data.get("pvdf_description")
                    )
                    proforma_details_instance.pvdf_price = proforma_detail_data.get(
                        "pvdf_price"
                    )
                    proforma_details_instance.laser_marking_description = (
                        proforma_detail_data.get("laser_marking_description")
                    )
                    proforma_details_instance.laser_marking_price = (
                        proforma_detail_data.get("laser_marking_price")
                    )
                    proforma_details_instance.length = proforma_detail_data.get(
                        "length", proforma_details_instance.length
                    )
                    proforma_details_instance.pieces = proforma_detail_data.get(
                        "pieces", proforma_details_instance.pieces
                    )
                    proforma_details_instance.net_weight = proforma_detail_data.get(
                        "net_weight", proforma_details_instance.net_weight
                    )
                    proforma_details_instance.nalco_rate = proforma_detail_data.get(
                        "nalco_rate", proforma_details_instance.nalco_rate
                    )
                    proforma_details_instance.packed_weight = proforma_detail_data.get(
                        "packed_weight", proforma_details_instance.packed_weight
                    )
                    proforma_details_instance.dispatch_qty = proforma_detail_data.get(
                        "dispatch_qty", proforma_details_instance.dispatch_qty
                    )

                    if "jobworks" in proforma_detail_data:
                        jobwork_types_data = proforma_detail_data.get("jobworks", [])
                        jobwork_type_instances = JobWorkType.objects.filter(
                            id__in=jobwork_types_data
                        )
                        proforma_details_instance.jobworks.set(jobwork_type_instances)

                    proforma_details_instance.updated_by = request.user
                    proforma_details_instance.updated_at = timezone.now()
                    proforma_details_instance.save()

                    proforma_details_ids.append(proforma_details_instance.id)

                else:
                    new_proforma_detail_instance = ProformaDetails.objects.create(
                        proforma=instance,
                        customer_reference_no=proforma_detail_data.get(
                            "customer_reference_no"
                        ),
                        profile_no=profile_no_instance,
                        temper=temper_instance,
                        alloy=alloy_instance,
                        out_source=proforma_detail_data.get("out_source", False),
                        cutting=proforma_detail_data.get("cutting"),
                        machining=proforma_detail_data.get("machining"),
                        deburring=proforma_detail_data.get("deburring"),
                        cutting_price=proforma_detail_data.get("cutting_price"),
                        machining_price=proforma_detail_data.get("machining_price"),
                        deburring_price=proforma_detail_data.get("deburring_price"),
                        anodising=proforma_detail_data.get("anodising"),
                        powder_coating=proforma_detail_data.get("powder_coating"),
                        pvdf=proforma_detail_data.get("pvdf"),
                        anodising_price=proforma_detail_data.get("anodising_price"),
                        anodising_description=proforma_detail_data.get(
                            "anodising_description"
                        ),
                        powder_coating_price=proforma_detail_data.get(
                            "powder_coating_price"
                        ),
                        powder_coating_description=proforma_detail_data.get(
                            "powder_coating_description"
                        ),
                        pvdf_price=proforma_detail_data.get("pvdf_price"),
                        pvdf_description=proforma_detail_data.get("pvdf_description"),
                        laser_marking_price=proforma_detail_data.get(
                            "laser_marking_price"
                        ),
                        laser_marking_description=proforma_detail_data.get(
                            "laser_marking_description"
                        ),
                        length=proforma_detail_data.get("length"),
                        pieces=proforma_detail_data.get("pieces"),
                        net_weight=proforma_detail_data.get("net_weight"),
                        nalco_rate=proforma_detail_data.get("nalco_rate"),
                        packed_weight=proforma_detail_data.get("packed_weight"),
                        dispatch_qty=proforma_detail_data.get("dispatch_qty"),
                        updated_by=request.user,
                        updated_at=timezone.now(),
                    )

                    jobwork_types_data = proforma_detail_data.get("jobworks", [])
                    if isinstance(jobwork_types_data, list):
                        jobwork_type_instances = JobWorkType.objects.filter(
                            id__in=jobwork_types_data
                        )
                        new_proforma_detail_instance.jobworks.set(
                            jobwork_type_instances
                        )

                    proforma_details_ids.append(new_proforma_detail_instance.id)

            ProformaDetails.objects.filter(proforma=instance).exclude(
                id__in=proforma_details_ids
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

        proforma_details_qs = ProformaDetails.objects.filter(
            proforma=instance, deleted=False
        )
        total_net_weight = Decimal("0.000")
        total_pieces = 0
        total_packing_cost = Decimal("0.00")
        total_basic_amount = Decimal("0.00")

        proforma_details_list = []

        for detail in proforma_details_qs:
            pkgd_weight = Decimal(detail.packed_weight or 0)
            net_weight = Decimal(detail.net_weight or 0)
            pieces = int(detail.pieces or 0)

            
            final_rate = (Decimal(detail.nalco_rate or 0) + Decimal(detail.conversion or 0))
            if instance.type == "WORKORDER":
                if detail.packed_weight is not None and detail.packed_weight > 0:
                    basic_amount = final_rate * pkgd_weight
                else:
                    basic_amount = final_rate * net_weight
            else:
                basic_amount = final_rate * net_weight

            cutting_price = Decimal(detail.cutting_price or 0) * pkgd_weight
            machining_price = Decimal(detail.machining_price or 0) * pkgd_weight
            deburring_price = Decimal(detail.deburring_price or 0) * pkgd_weight
            anodising_price = Decimal(detail.anodising_price or 0) * pkgd_weight
            powder_coating_price = (
                Decimal(detail.powder_coating_price or 0) * pkgd_weight
            )
            pvdf_price = Decimal(detail.pvdf_price or 0) * pkgd_weight
            laser_marking_price = Decimal(detail.laser_marking_price or 0) * pkgd_weight

            workorder_detail = WorkOrderDetail.objects.filter(
                workorder_id=instance.workorder_id,
                die_profile_id=detail.profile_no_id,
            ).first()

            total_packing_rate = (instance.packing_mode.aggregate(total=Sum("price_per_kg"))["total"] or Decimal("0.00"))
            print("total_packing_rate", total_packing_rate)
            if instance.type == "WORKORDER":
                if detail.packed_weight is not None and detail.packed_weight > 0:
                    packing_cost = total_packing_rate * pkgd_weight
                else:
                    packing_cost = total_packing_rate * net_weight
            else:
                packing_cost = total_packing_rate * net_weight
            # packing_cost = total_packing_rate * pkgd_weight
            total_packing_cost += packing_cost
            # packing_cost = (
            #     workorder_detail.packing_cost if workorder_detail else Decimal("0.00")
            # ) * pkgd_weight
            # total_packing_cost += packing_cost

            additional_total = (
                cutting_price
                + machining_price
                + deburring_price
                + anodising_price
                + powder_coating_price
                + pvdf_price
                + laser_marking_price
            )

            line_total = (basic_amount + additional_total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_basic_amount += line_total
            total_net_weight += pkgd_weight if pkgd_weight else net_weight
            total_pieces += pieces

            detail_data = ProformaDetailsSerializers(detail, context=self.context).data
            detail_data["final_rate"] = (
                (detail.nalco_rate or 0)
                + (detail.conversion or 0)
            )
            detail_data["total_amount"] = "{:.2f}".format(Decimal(detail_data["final_rate"]) * Decimal(detail.net_weight))
            detail_data["total_basic_amount"] = format(basic_amount, ".2f")
            proforma_details_list.append(detail_data)

        total_basic_amount = total_basic_amount.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_packing_cost = total_packing_cost.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        ret["proforma_details"] = proforma_details_list

        freight_charges = Decimal(instance.freight_charges or 0).quantize(
            Decimal("0.01")
        )
        transport_charges = Decimal(instance.transport_charges or 0).quantize(
            Decimal("0.01")
        )
        insurance_charges = Decimal(instance.insurance_charges or 0).quantize(
            Decimal("0.01")
        )
        other_charges = Decimal(instance.other_charges or 0).quantize(Decimal("0.01"))
        advance_amount = Decimal(instance.advance_amount or 0)

        taxable_value = (
            total_basic_amount
            + freight_charges
            + transport_charges
            + insurance_charges
            + other_charges
            + total_packing_cost
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        gst_rate = Decimal("18") / Decimal("100")

        if is_igst:
            igst = (taxable_value * gst_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
        else:
            cgst = (taxable_value * gst_rate / 2).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            sgst = (taxable_value * gst_rate / 2).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            igst = Decimal("0.00")

        total_gst = (igst + cgst + sgst).quantize(Decimal("0.01"))

        igst = igst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cgst = cgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = sgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_gst = igst + cgst + sgst

        total_grand_total = (taxable_value + total_gst).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        total_payable = (taxable_value + total_gst).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        rounded_total = total_payable.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        round_off = (rounded_total - total_payable).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        final_amount = (rounded_total - abs(advance_amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        detail_data["gst_amount"] = format(total_gst, ".2f")

        ret["summary"] = {
            "gst_type": gst_type_name,
            "freight_charges": format(freight_charges, ".2f"),
            "transport_charges": format(transport_charges, ".2f"),
            "insurance_charges": format(insurance_charges, ".2f"),
            "other_charges": format(other_charges, ".2f"),
            "packing_cost": format(total_packing_cost, ".2f"),
            "igst": format(igst, ".2f"),
            "cgst": format(cgst, ".2f"),
            "sgst": format(sgst, ".2f"),
            "total_basic_amount": format(total_basic_amount, ".2f"),
            "taxable_value": format(taxable_value, ".2f"),
            "total_gst": format(total_gst, ".2f"),
            "total_grand_total": format(total_grand_total, ".2f"),
            "advance_amount": format(advance_amount, ".2f"),
            "total_payable_amount": format(final_amount, ".2f"),
            "round_off": format(round_off, ".2f"),
            "final_amount": format(rounded_total, ".2f"),
            "total_net_weight": format(total_net_weight, ".3f"),
            "total_pieces": total_pieces,
        }

        return ret
