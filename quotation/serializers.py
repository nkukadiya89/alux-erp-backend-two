from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from common.models import GstType, JobWorkType, PackingMode
from common.serializers import (
    BaseModelSerializer,
    JobWorkSerializer,
    PackingModeSortSerializer,
)
from customer.serializers import BankingDetailSerializer
from customer.sort_serializers import CustomerSortListSerializer, CustomerSortSerializer
from die.models import Die
from die.sort_serializers import DieSortSerializers
from product.models import Alloy, Temper
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from quotation.models import Quotation, QuotationDetail
from utils.calculate_weight_range import get_quatation_weight_range
from utils.generate_number import generate_quotation_no


class QuotationDetailSerializers(BaseModelSerializer):
    weight_range = serializers.SerializerMethodField()
    jobworks_detail = JobWorkSerializer(source="jobworks", many=True, read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = QuotationDetail
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "die_profile",
            "alloy",
            "temper",
            "customer_reference_no",
            "length",
            "pieces",
            "net_weight",
            "jobworks",
            "jobworks_detail",
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
            "anodising_description",
            "powder_coating_price",
            "powder_coating_description",
            "pvdf_price",
            "pvdf_description",
            "laser_marking_description",
            "laser_marking_price",
            "unit_of_measurement",
            "price_per_kg",
            "description",
            "conversion",
            "weight_range",
        ]

    def get_weight_range(self, obj):
        die_profile_wt_kg_p_mt = obj.die_profile.wt_kg_p_mt
        length = obj.length
        fixed_tolerance = "+-10%"

        return get_quatation_weight_range(
            die_profile_wt_kg_p_mt, length, fixed_tolerance
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "die_profile" in ret:
            ret["die_profile"] = DieSortSerializers(instance.die_profile).data

        if "alloy" in ret:
            ret["alloy"] = AlloySortSerializers(instance.alloy).data

        if "temper" in ret:
            ret["temper"] = TemperSortSerializers(instance.temper).data
        return ret


class QuotationDetailSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = QuotationDetail
        fields = [
            "id",
            "die_profile",
            "alloy",
        ]


class QuotationSerializers(BaseModelSerializer):
    quotation_details = serializers.ListField(required=False)
    packing_mode = serializers.PrimaryKeyRelatedField(
        queryset=PackingMode.objects.filter(deleted=False),
        many=True,
        required=False,
    )
    packing_mode_details = PackingModeSortSerializer(
        source="packing_mode",
        many=True,
        read_only=True,
    )

    class Meta(BaseModelSerializer.Meta):
        model = Quotation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer",
            "quotation_date",
            "project_name",
            "terms_and_condition",
            "remarks",
            "quotation_no",
            "converted_date",
            "packing_mode",
            "packing_mode_details",
            "status",
            "workorder_no",
            "quotation_details",
        ]

    def get_instance(self, model, id, error_message):
        try:
            return model.objects.get(id=id)
        except model.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": error_message}
            )

    def create(self, validated_data):
        packing_modes_data = validated_data.pop("packing_mode", [])
        validated_data["quotation_no"] = generate_quotation_no(self)

        quotation_details_data = validated_data.pop("quotation_details", None)

        validated_data["created_by"] = self.context["request"].user

        quotation_instance = Quotation.objects.create(**validated_data)

        if packing_modes_data:
            quotation_instance.packing_mode.set(packing_modes_data)

        if quotation_details_data is not None:
            for quotation_detail_data in quotation_details_data:

                jobwork_ids = quotation_detail_data.pop("jobworks", [])
                jobwork_instances = []
                if isinstance(jobwork_ids, list) and jobwork_ids:
                    jobwork_instances = list(
                        JobWorkType.objects.filter(id__in=jobwork_ids)
                    )

                die_profile_id = quotation_detail_data.pop("die_profile", None)
                alloy_id = quotation_detail_data.pop("alloy", None)
                temper_id = quotation_detail_data.pop("temper", None)

                if die_profile_id is not None:
                    quotation_detail_data["die_profile"] = self.get_instance(
                        Die, die_profile_id, "Die Not Found"
                    )
                if alloy_id is not None:
                    quotation_detail_data["alloy"] = self.get_instance(
                        Alloy, alloy_id, "Alloy Not Found"
                    )
                if temper_id is not None:
                    quotation_detail_data["temper"] = self.get_instance(
                        Temper, temper_id, "Temper Not Found"
                    )

                quotation_detail_data["quotation"] = quotation_instance
                quotation_detail_data["created_by"] = self.context["request"].user
                quotation_detail_data["created_at"] = datetime.now()

                quotation_detail_instance = QuotationDetail.objects.create(
                    **quotation_detail_data
                )

                if jobwork_instances:
                    quotation_detail_instance.jobworks.set(jobwork_instances)

        return quotation_instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        packing_modes_data = validated_data.pop("packing_mode", None)

        for field in [
            "customer",
            "quotation_date",
            "project_name",
            "terms_and_condition",
            "quotation_no",
            "remarks",
            "converted_date",
            "status",
            "workorder_no",
        ]:
            setattr(
                instance, field, validated_data.get(field, getattr(instance, field))
            )

        instance.updated_by = request.user
        instance.updated_at = timezone.now()

        if packing_modes_data is not None:
            instance.packing_mode.set(packing_modes_data)

        quotation_details_data = validated_data.pop("quotation_details", None)
        quotation_details_ids = []

        if quotation_details_data is not None:
            for quotation_detail_data in quotation_details_data:
                detail_id = quotation_detail_data.get("id")

                if detail_id:
                    try:
                        details_instance = QuotationDetail.objects.get(
                            id=detail_id, quotation=instance
                        )
                    except QuotationDetail.DoesNotExist:
                        raise serializers.ValidationError(
                            {"success": False, "message": "Quotation Detail Not Found."}
                        )

                    die_profile_id = quotation_detail_data.pop("die_profile", None)
                    alloy_id = quotation_detail_data.pop("alloy", None)
                    temper_id = quotation_detail_data.pop("temper", None)

                    if die_profile_id is not None:
                        details_instance.die_profile = self.get_instance(
                            Die, die_profile_id, "Die Not Found"
                        )
                    if alloy_id is not None:
                        details_instance.alloy = self.get_instance(
                            Alloy, alloy_id, "Alloy Not Found"
                        )
                    if temper_id is not None:
                        details_instance.temper = self.get_instance(
                            Temper, temper_id, "Temper Not Found"
                        )

                    for field in [
                        "customer_reference_no",
                        "length",
                        "pieces",
                        "net_weight",
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
                        "anodising_description",
                        "anodising_price",
                        "powder_coating_description",
                        "powder_coating_price",
                        "pvdf_description",
                        "pvdf_price",
                        "laser_marking_description",
                        "laser_marking_price",
                        "price_per_kg",
                        "unit_of_measurement",
                        "description",
                        "conversion",
                    ]:
                        if field in quotation_detail_data:
                            setattr(
                                details_instance, field, quotation_detail_data[field]
                            )

                    if "jobworks" in quotation_detail_data:
                        jobwork_types_data = quotation_detail_data.get("jobworks", [])
                        jobwork_type_instances = JobWorkType.objects.filter(
                            id__in=jobwork_types_data
                        )
                        details_instance.jobworks.set(jobwork_type_instances)

                    details_instance.updated_by = request.user
                    details_instance.updated_at = timezone.now()
                    details_instance.save()

                    quotation_details_ids.append(details_instance.id)

                else:
                    new_detail_data = {
                        "quotation": instance,
                        "customer_reference_no": quotation_detail_data.get(
                            "customer_reference_no"
                        ),
                        "length": quotation_detail_data.get("length"),
                        "pieces": quotation_detail_data.get("pieces"),
                        "net_weight": quotation_detail_data.get("net_weight"),
                        "out_source": quotation_detail_data.get("out_source", False),
                        "cutting": quotation_detail_data.get("cutting", False),
                        "machining": quotation_detail_data.get("machining", False),
                        "deburring": quotation_detail_data.get("deburring", False),
                        "cutting_price": quotation_detail_data.get("cutting_price"),
                        "machining_price": quotation_detail_data.get("machining_price"),
                        "deburring_price": quotation_detail_data.get("deburring_price"),
                        "anodising": quotation_detail_data.get("anodising", False),
                        "powder_coating": quotation_detail_data.get(
                            "powder_coating", False
                        ),
                        "pvdf": quotation_detail_data.get("pvdf", False),
                        "anodising_description": quotation_detail_data.get(
                            "anodising_description"
                        ),
                        "anodising_price": quotation_detail_data.get("anodising_price"),
                        "powder_coating_description": quotation_detail_data.get(
                            "powder_coating_description"
                        ),
                        "powder_coating_price": quotation_detail_data.get(
                            "powder_coating_price"
                        ),
                        "pvdf_description": quotation_detail_data.get(
                            "pvdf_description"
                        ),
                        "pvdf_price": quotation_detail_data.get("pvdf_price"),
                        "laser_marking_description": quotation_detail_data.get(
                            "laser_marking_description"
                        ),
                        "laser_marking_price": quotation_detail_data.get(
                            "laser_marking_price"
                        ),
                        "price_per_kg": quotation_detail_data.get("price_per_kg"),
                        "unit_of_measurement": quotation_detail_data.get(
                            "unit_of_measurement"
                        ),
                        "description": quotation_detail_data.get("description"),
                        "conversion": quotation_detail_data.get("conversion"),
                        "updated_by": request.user,
                        "updated_at": timezone.now(),
                    }

                    die_profile_id = quotation_detail_data.get("die_profile")
                    alloy_id = quotation_detail_data.get("alloy")
                    temper_id = quotation_detail_data.get("temper")

                    if die_profile_id is not None:
                        new_detail_data["die_profile"] = self.get_instance(
                            Die, die_profile_id, "Die Not Found"
                        )
                    if alloy_id is not None:
                        new_detail_data["alloy"] = self.get_instance(
                            Alloy, alloy_id, "Alloy Not Found"
                        )
                    if temper_id is not None:
                        new_detail_data["temper"] = self.get_instance(
                            Temper, temper_id, "Temper Not Found"
                        )

                    new_detail_instance = QuotationDetail.objects.create(
                        **new_detail_data
                    )

                    jobwork_types_data = quotation_detail_data.get("jobworks", [])
                    if isinstance(jobwork_types_data, list):
                        jobwork_type_instances = JobWorkType.objects.filter(
                            id__in=jobwork_types_data
                        )
                        new_detail_instance.jobworks.set(jobwork_type_instances)

                    quotation_details_ids.append(new_detail_instance.id)

            QuotationDetail.objects.filter(quotation=instance).exclude(
                id__in=quotation_details_ids
            ).update(deleted=True)

        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if instance.customer:
            customer_data = CustomerSortSerializer(instance.customer).data
            customer_data["banking_details"] = (
                BankingDetailSerializer(
                    instance.customer.banking_details.all(), many=True
                ).data
                if hasattr(instance.customer, "banking_details")
                else []
            )   
            ret["customer"] = customer_data

        quotation_details = instance.quotation_quotation_detail.filter(deleted=False)
        quotation_data = QuotationDetailSerializers(
            quotation_details.order_by("id"), many=True, context=self.context
        ).data

        total_pieces = 0
        total_net_weight = Decimal(0)
        total_basic_amount = Decimal(0)
        total_gst_amount = Decimal(0)

        gst_percentage = Decimal(0)
        if instance.customer and instance.customer.applicable_gst:
            applicable_gst = instance.customer.applicable_gst.strip()
            if applicable_gst == "sgst_cgst":
                sgst = GstType.objects.filter(name="sgst").first()
                cgst = GstType.objects.filter(name="cgst").first()
                sgst_percentage = Decimal(sgst.percentage or 0) if sgst else Decimal(0)
                cgst_percentage = Decimal(cgst.percentage or 0) if cgst else Decimal(0)
                gst_percentage = sgst_percentage + cgst_percentage
            else:
                gst_type = GstType.objects.filter(name=applicable_gst).first()
                gst_percentage = (
                    Decimal(gst_type.percentage or 0) if gst_type else Decimal(0)
                )

        for detail in quotation_details:
            pieces = detail.pieces or 0
            net_weight = Decimal(detail.net_weight or 0)
            price_per_kg = Decimal(detail.price_per_kg or 0)
            conversation = Decimal(detail.conversion or 0)

            total_pieces += pieces
            total_net_weight += net_weight

            cutting_price = Decimal(detail.cutting_price or 0) * net_weight
            machining_price = Decimal(detail.machining_price or 0) * net_weight
            deburring_price = Decimal(detail.deburring_price or 0) * net_weight
            anodising_price = Decimal(detail.anodising_price or 0) * net_weight
            powder_coating_price = (
                Decimal(detail.powder_coating_price or 0) * net_weight
            )
            pvdf_price = Decimal(detail.pvdf_price or 0) * net_weight
            laser_marking_price = Decimal(detail.laser_marking_price or 0) * net_weight

            total_basic_amount_detail = (price_per_kg + conversation) * net_weight
            additional_prices_total = (
                cutting_price
                + machining_price
                + deburring_price
                + anodising_price
                + powder_coating_price
                + pvdf_price
                + laser_marking_price
            )
            total_basic_amount_detail += additional_prices_total
            total_basic_amount += total_basic_amount_detail

            gst_rate_detail = (
                gst_percentage / Decimal(100)
            ) * total_basic_amount_detail
            total_gst_amount += gst_rate_detail
            total_amount_detail = total_basic_amount_detail + gst_rate_detail

            for data in quotation_data:
                if data["id"] == detail.id:
                    data["net_weight"] = format(net_weight, ".3f")
                    data["total_basic_amount"] = round(total_basic_amount_detail, 2)
                    data["gst_rate"] = round(gst_rate_detail, 2)
                    data["total_amount"] = round(total_amount_detail, 2)
                    data["jobwork_prices_total"] = round(additional_prices_total, 2)

        ret["quotation_details"] = quotation_data
        ret["total_pieces"] = total_pieces
        ret["total_net_weight"] = total_net_weight
        ret["total_basic_amount"] = round(total_basic_amount, 2)
        ret["total_gst_amount"] = round(total_gst_amount, 2)
        ret["total_amount"] = round(total_basic_amount + total_gst_amount, 2)

        if not quotation_details:
            quotation_details = [
                {
                    "id": None,
                    "die_profile": None,
                    "alloy": None,
                    "temper": None,
                    "customer_reference_no": None,
                    "length": None,
                    "pieces": None,
                    "net_weight": None,
                    "out_source": False,
                    "cutting": None,
                    "machining": None,
                    "deburring": None,
                    "cutting_price": None,
                    "machining_price": None,
                    "deburring_price": None,
                    "anodising": None,
                    "powder_coating": None,
                    "pvdf": None,
                    "anodising_description": None,
                    "anodising_price": None,
                    "powder_coating_description": None,
                    "powder_coating_price": None,
                    "pvdf_description": None,
                    "pvdf_price": None,
                    "laser_marking_description": None,
                    "laser_marking_price": None,
                    "unit_of_measurement": None,
                    "price_per_kg": None,
                    "description": None,
                    "conversion": None,
                }
            ]

        return ret


class QuotationListSerializers(BaseModelSerializer):
    customer = CustomerSortListSerializer(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Quotation
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "customer",
            "quotation_no",
            "quotation_date",
            "workorder_no",
            "converted_date",
            "status",
        ]


class QuotationSortSerializers(serializers.ModelSerializer):

    class Meta:
        model = Quotation
        fields = [
            "id",
            "quotation_date",
        ]
