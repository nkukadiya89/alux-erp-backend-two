from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from common.models import GstType
from settings.models import TaxComplianceSettings
from common.serializers import BaseModelSerializer
from customer.sort_serializers import CustomerSortListSerializer, CustomerSortSerializer
from die.models import Die
from die.sort_serializers import DieSortSerializers
from die_quotation.models import DieQuotation, DieQuotationDetails
from product.models import Alloy
from product.models import Temper
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from utils.generate_number import (
    extract_inquiry_base_number,
    generate_die_inquiry_number,
    generate_die_quotation_no,
)


class DieQuotationListSerializer(BaseModelSerializer):
    customer = CustomerSortListSerializer(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = DieQuotation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer",
            "die_quotation_no",
            "quotation_date",
            "minimum_order_qty",
            "die_right",
        ]


class DieQuotationDetailsSerializers(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DieQuotationDetails
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "profile_no",
            "customer_reference_no",
            "alloy",
            "temper",
            "price_per_kg",
            "conversion",
            "description",
            "press_capacity",
            "quantity",
            "unit_of_measurement",
            "profile_devlopment_cost",
            "inquiry_number",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "alloy" in ret:
            ret["alloy"] = AlloySortSerializers(instance.alloy).data

        if "temper" in ret:
            ret["temper"] = TemperSortSerializers(instance.temper).data

        if "profile_no" in ret:
            ret["profile_no"] = DieSortSerializers(instance.profile_no).data

        return ret


class DieQuotationDetailsSortSerializers(serializers.ModelSerializer):

    class Meta:
        model = DieQuotationDetails
        fields = [
            "id",
            "profile_no",
            "customer_reference_no",
        ]


class DieQuotationSerializers(BaseModelSerializer):
    die_quotation_details = serializers.ListField(required=False)

    class Meta(BaseModelSerializer.Meta):
        model = DieQuotation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer",
            "minimum_order_qty",
            "die_right",
            "sample_delivery",
            "terms_and_condition",
            "quotation_date",
            "die_quotation_no",
            "die_quotation_details",
        ]

    def get_instance(self, model, id, error_message):
        try:
            return model.objects.get(id=id)
        except model.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": error_message}
            )

    def create(self, validated_data):
        die_quotation_details_data = validated_data.pop("die_quotation_details", None)

        validated_data["created_by"] = self.context["request"].user

        validated_data["die_quotation_no"] = generate_die_quotation_no(self)

        last_quotation = DieQuotation.objects.order_by("-id").first()
        last_base_number = 0
        if last_quotation and last_quotation.inquiry_base_number:
            try:
                last_base_number = int(last_quotation.inquiry_base_number)
            except ValueError:
                last_base_number = 0
        new_base_number = str(last_base_number + 1).zfill(5)
        validated_data["inquiry_base_number"] = new_base_number

        die_quotation_instance = DieQuotation.objects.create(**validated_data)

        if die_quotation_details_data is not None:
            for index, die_quotation_detail_data in enumerate(
                die_quotation_details_data, start=1
            ):
                profile_no_id = die_quotation_detail_data.pop("profile_no", None)
                if profile_no_id is not None:
                    try:
                        die_instance = Die.objects.get(id=profile_no_id)
                        die_quotation_detail_data["profile_no"] = die_instance
                    except Die.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Die instance not found."}
                        )

                alloy_id = die_quotation_detail_data.pop("alloy", None)
                if alloy_id is not None:
                    try:
                        alloy_instance = Alloy.objects.get(id=alloy_id)
                        die_quotation_detail_data["alloy"] = alloy_instance
                    except Alloy.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Alloy instance not found."}
                        )
                    
                temper_id = die_quotation_detail_data.pop("temper", None)
                if temper_id is not None:
                    try:
                        temper_instance = Temper.objects.get(id=temper_id)
                        die_quotation_detail_data["temper"] = temper_instance
                    except Temper.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Temper instance not found."}
                        )
    

                die_quotation_detail_data["die_quotation"] = die_quotation_instance
                die_quotation_detail_data["created_by"] = self.context["request"].user
                die_quotation_detail_data["created_at"] = timezone.now()

                base_number = extract_inquiry_base_number(new_base_number)
                inquiry_number = generate_die_inquiry_number(base_number, index)
                die_quotation_detail_data["inquiry_number"] = inquiry_number

                DieQuotationDetails.objects.create(**die_quotation_detail_data)

        return die_quotation_instance

    def update(self, instance, validated_data):
        request = self.context.get("request")

        instance.customer = validated_data.get("customer", instance.customer)
        instance.minimum_order_qty = validated_data.get(
            "minimum_order_qty", instance.minimum_order_qty
        )
        instance.die_right = validated_data.get("die_right", instance.die_right)
        instance.sample_delivery = validated_data.get(
            "sample_delivery", instance.sample_delivery
        )
        instance.terms_and_condition = validated_data.get(
            "terms_and_condition", instance.terms_and_condition
        )
        instance.quotation_date = validated_data.get(
            "quotation_date", instance.quotation_date
        )
        instance.die_quotation_no = validated_data.get(
            "die_quotation_no", instance.die_quotation_no
        )
        instance.updated_by = request.user
        instance.updated_at = timezone.now()

        die_quotation_details_data = validated_data.pop("die_quotation_details", None)
        die_quotation_details_instances = []
        new_die_quotation_details_instances = []

        if die_quotation_details_data is not None:
            die_quotation_details_ids = []

            detail_index = DieQuotationDetails.objects.filter(
                die_quotation=instance
            ).count()

            for die_quotation_detail_data in die_quotation_details_data:
                die_quotation_detail_id = die_quotation_detail_data.get("id")
                die_quotation_details_ids.append(die_quotation_detail_id)

                die_detail_id = die_quotation_detail_data.get("id")
                new_die_quotation_detail_instance = None
                if die_detail_id:
                    try:
                        die_details_instance = DieQuotationDetails.objects.get(
                            id=die_detail_id
                        )
                    except DieQuotationDetails.DoesNotExist:
                        raise serializers.ValidationError(
                            {
                                "success": False,
                                "message": "Die Quotation Detail not found.",
                            }
                        )

                    profile_no_id = die_quotation_detail_data.pop("profile_no", None)
                    alloy_id = die_quotation_detail_data.pop("alloy", None)
                    temper_id = die_quotation_detail_data.pop("temper", None)

                    if profile_no_id is not None:
                        try:
                            die_details_instance.profile_no = Die.objects.get(
                                id=profile_no_id
                            )
                        except Die.DoesNotExist:
                            raise serializers.ValidationError(
                                {"success": False, "message": "Die not found."}
                            )

                    if alloy_id is not None:
                        try:
                            die_details_instance.alloy = Alloy.objects.get(id=alloy_id)
                        except Alloy.DoesNotExist:
                            raise serializers.ValidationError(
                                {"success": False, "message": "Alloy not found."}
                            )
                    if temper_id is not None:
                        try:
                            die_details_instance.temper = Temper.objects.get(id=temper_id)
                        except Temper.DoesNotExist:
                            raise serializers.ValidationError(
                                {"success": False, "message": "Temper not found."}
                            )
                    die_details_instance.description = (
                        die_quotation_detail_data.get("description")
                    )
                    die_details_instance.press_capacity = die_quotation_detail_data.get(
                        "press_capacity"
                    )
                    die_details_instance.quantity = die_quotation_detail_data.get(
                        "quantity"
                    )
                    die_details_instance.profile_devlopment_cost = (
                        die_quotation_detail_data.get("profile_devlopment_cost")
                    )
                    die_details_instance.unit_of_measurement = (
                        die_quotation_detail_data.get("unit_of_measurement")
                    )
                    die_details_instance.price_per_kg = (
                        die_quotation_detail_data.get("price_per_kg")
                    )
                    die_details_instance.conversion = (
                        die_quotation_detail_data.get("conversion")
                    )
                    die_details_instance.updated_by = request.user
                    die_details_instance.updated_at = timezone.now()
                    die_details_instance.save()
                    die_quotation_details_instances.append(die_details_instance)

                else:
                    detail_index += 1
                    base_number = extract_inquiry_base_number(
                        instance.inquiry_base_number
                    )
                    inquiry_number = generate_die_inquiry_number(
                        base_number, detail_index
                    )

                    new_die_quotation_data = {
                        "die_quotation": instance,
                        "description": die_quotation_detail_data.get("description"),
                        "press_capacity": die_quotation_detail_data.get(
                            "press_capacity"
                        ),
                        "quantity": die_quotation_detail_data.get("quantity"),
                        "profile_devlopment_cost": die_quotation_detail_data.get(
                            "profile_devlopment_cost"
                        ),
                        "unit_of_measurement": die_quotation_detail_data.get(
                            "unit_of_measurement"
                        ),
                        "price_per_kg": die_quotation_detail_data.get("price_per_kg"),
                        "conversion": die_quotation_detail_data.get("conversion"),
                        "updated_by": request.user,
                        "updated_at": timezone.now(),
                        "inquiry_number": inquiry_number,
                    }

                    profile_no_id = die_quotation_detail_data.get("profile_no")
                    alloy_id = die_quotation_detail_data.get("alloy")
                    temper_id = die_quotation_detail_data.get("temper")

                    if profile_no_id is not None:
                        new_die_quotation_data["profile_no"] = self.get_instance(
                            Die, profile_no_id, "Die Not Found"
                        )
                    if alloy_id is not None:
                        new_die_quotation_data["alloy"] = self.get_instance(
                            Alloy, alloy_id, "Alloy Not Found"
                        )
                    if temper_id is not None:
                        new_die_quotation_data["temper"] = self.get_instance(
                            Temper, temper_id, "Temper Not Found"
                        )    

                    new_die_quotation_detail_instance = (
                        DieQuotationDetails.objects.create(**new_die_quotation_data)
                    )
                    new_die_quotation_details_instances.append(
                        new_die_quotation_detail_instance
                    )
                    die_quotation_details_ids.append(
                        new_die_quotation_detail_instance.id
                    )

            if len(die_quotation_details_ids) > 0:
                if new_die_quotation_detail_instance:
                    die_detail_ids = [
                        die_detail.id
                        for die_detail in new_die_quotation_details_instances
                    ]
                    DieQuotationDetails.objects.filter(die_quotation=instance).exclude(
                        id__in=die_quotation_details_ids
                    ).exclude(id__in=die_detail_ids).update(deleted=True)
                else:
                    DieQuotationDetails.objects.filter(die_quotation=instance).exclude(
                        id__in=die_quotation_details_ids
                    ).update(deleted=True)

        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "customer" in ret:
            ret["customer"] = CustomerSortSerializer(instance.customer).data

        die_quotation_details = []
        try:
            die_quotation_details = DieQuotationDetailsSerializers(
                DieQuotationDetails.objects.filter(
                    die_quotation=instance, deleted=False
                ),
                many=True,
            ).data

        except DieQuotationDetails.DoesNotExist:
            pass

        if not die_quotation_details:
            die_quotation_details = [
                {
                    "id": None,
                    "profile_no": None,
                    "customer_reference_no": None,
                    "alloy": None,
                    "press_capacity": None,
                    "quantity": None,
                    "unit_of_measurement": None,
                    "profile_devlopment_cost": None,
                    "inquiry_number": None,
                }
            ]

        customer = instance.customer
        applicable_gst = customer.applicable_gst if customer else None

        # GST %
        tax_setting = TaxComplianceSettings.objects.first()
        cgst_percent = Decimal(str(tax_setting.cgst or 0))
        sgst_percent = Decimal(str(tax_setting.sgst or 0))
        igst_percent = Decimal(str(tax_setting.igst or 0))

        if applicable_gst:
            if applicable_gst.lower() == "sgst_cgst":
                cgst_percent = Decimal(str(cgst_percent)) if cgst_percent else Decimal("0.00")
                sgst_percent = Decimal(str(sgst_percent)) if sgst_percent else Decimal("0.00")
            else:
                igst_percent = Decimal(str(igst_percent)) if igst_percent else Decimal("0.00")

        gross_amount = Decimal("0.00")
        total_quantity = Decimal("0.00")

        detail_data = []

        for detail in DieQuotationDetails.objects.filter(
            die_quotation=instance, deleted=False
        ):
            quantity = Decimal(str(detail.quantity or 0))
            profile_devlopment_cost = Decimal(str(detail.profile_devlopment_cost or 0))

            # Amount = Profile Development Cost × Quantity
            basic_amount = profile_devlopment_cost * quantity

            gst_percent = (
                igst_percent
                if applicable_gst and applicable_gst.upper() == "IGST"
                else (cgst_percent + sgst_percent)
            )

            gst_amount = (basic_amount * gst_percent) / Decimal("100")
            total_amount = basic_amount + gst_amount

            detail_data.append(
                {
                    "id": detail.id,
                    "profile_no": (
                        DieSortSerializers(detail.profile_no).data
                        if detail.profile_no
                        else None
                    ),
                    "customer_reference_no": detail.customer_reference_no,
                    "description": detail.description,
                    "alloy": (
                        AlloySortSerializers(detail.alloy).data
                        if detail.alloy
                        else None
                    ),
                    "temper": (
                        TemperSortSerializers(detail.temper).data
                        if detail.temper
                        else None
                    ),
                    "press_capacity": detail.press_capacity,
                    "quantity": detail.quantity,
                    "price_per_kg": detail.price_per_kg,
                    "conversion": detail.conversion,
                    "unit_of_measurement": detail.unit_of_measurement,
                    "inquiry_number": detail.inquiry_number,
                    "profile_devlopment_cost": detail.profile_devlopment_cost,
                    "gst_percent": float(gst_percent),
                    "gst_amount": float(gst_amount),
                    "total_amount": float(total_amount),
                }
            )
            gross_amount += basic_amount
            total_quantity += quantity
            # Summary
            sub_total = gross_amount

            cgst_amount = Decimal("0.00")
            sgst_amount = Decimal("0.00")
            igst_amount = Decimal("0.00")

            if applicable_gst:
                if applicable_gst.upper() == "SGST_CGST":
                    cgst_amount = (sub_total * cgst_percent) / Decimal("100")
                    sgst_amount = (sub_total * sgst_percent) / Decimal("100")
                else:
                    igst_amount = (sub_total * igst_percent) / Decimal("100")

            round_off = Decimal("0.00")

            total_amount = (
                sub_total
                + cgst_amount
                + sgst_amount
                + igst_amount
                + round_off
            )

        ret["die_quotation_details"] = detail_data

        ret["summary"] = {
            "gross_amount": round(float(gross_amount), 2),
            "sub_total": round(float(sub_total), 2),
            "cgst_percent": float(cgst_percent),
            "cgst_amount": round(float(cgst_amount), 2),
            "sgst_percent": float(sgst_percent),
            "sgst_amount": round(float(sgst_amount), 2),
            "igst_percent": float(igst_percent),
            "igst_amount": round(float(igst_amount), 2),
            "round_off": round(float(round_off), 2),
            "total_amount": round(float(total_amount), 2),
            "total_quantity": float(total_quantity),
        }

        return ret


class DieQuotationSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = DieQuotation
        fields = [
            "id",
            "customer",
        ]
