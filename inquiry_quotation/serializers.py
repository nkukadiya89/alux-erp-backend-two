from decimal import Decimal

from rest_framework import serializers

from common.models import JobWorkType
from inquiry.serializers import (
    AlloySerializer,
    JobWorkTypeSerializer,
    TemperSerializer,
    UserQuickSerializer,
    TrimmedDecimalField
)
from inquiry_quotation.models import InquiryQuotation, InquiryQuotationDetail
from product.models import Alloy, Temper


class InquiryQuotationDetailCreateSerializer(serializers.ModelSerializer):
    alloy = serializers.PrimaryKeyRelatedField(
        queryset=Alloy.objects.all(), required=False, allow_null=True
    )
    temper = serializers.PrimaryKeyRelatedField(
        queryset=Temper.objects.all(), required=False, allow_null=True
    )
    surface_finish = serializers.PrimaryKeyRelatedField(
        queryset=JobWorkType.objects.all(), required=False, allow_null=True, many=True
    )

    class Meta:
        model = InquiryQuotationDetail
        fields = [
            "section_no",
            "alloy",
            "temper",
            "length",
            "price_per_kg",
            "conversion",
            "packing_cost",
            "net_weight",
            "quantity",
            "surface_finish",
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
            "laser_marking_price",
            "laser_marking_description",
        ]


class InquiryQuotationDetailSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    inquiry_quotation_detail = serializers.SerializerMethodField()
    alloy_detail = AlloySerializer(source="alloy", read_only=True)
    temper_detail = TemperSerializer(source="temper", read_only=True)
    surface_finish_detail = JobWorkTypeSerializer(
        source="surface_finish", read_only=True, many=True
    )
    length = TrimmedDecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = InquiryQuotationDetail
        fields = [
            "id",
            "inquiry_quotation",
            "inquiry_quotation_detail",
            "section_no",
            "alloy",
            "alloy_detail",
            "temper",
            "temper_detail",
            "surface_finish",
            "surface_finish_detail",
            "length",
            "price_per_kg",
            "conversion",
            "packing_cost",
            "net_weight",
            "quantity",
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
            "laser_marking_price",
            "laser_marking_description",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted",
        ]

    def get_inquiry_quotation_detail(self, obj):
        if obj.inquiry_quotation:
            iq = obj.inquiry_quotation
            revision = iq.revision_number
            return {
                "id": iq.id,
                "quotation_no": iq.quotation_no,
                "customer_name": (
                    iq.inquiry.customer_name if iq.inquiry else None
                ),
            }
        return None

class InquiryQuotationCreateSerializer(serializers.ModelSerializer):
    inquiry_quotation_details = InquiryQuotationDetailCreateSerializer(
        many=True, required=False
    )

    class Meta:
        model = InquiryQuotation
        fields = [
            "id",
            "inquiry",
            "quotation_no",
            "quotation_date",
            "terms_and_condition",
            "status",
            "converted_date",
            "remarks",
            "inquiry_quotation_details",
        ]

    def create(self, validated_data):
        inquiry_quotation_details_data = validated_data.pop(
            "inquiry_quotation_details", []
        )
        inquiry_quotation = InquiryQuotation.objects.create(**validated_data)

        self.context["inquiry_quotation_details_data"] = inquiry_quotation_details_data
        return inquiry_quotation


class InquiryQuotationListSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    customer_name = serializers.CharField(
        source="inquiry.customer_name", read_only=True
    )
    inquiry_number = serializers.CharField(
        source="inquiry.inquiry_number", read_only=True
    )

    class Meta:
        model = InquiryQuotation
        fields = [
            "id",
            "inquiry",
            "inquiry_number",
            "customer_name",
            "converted_date",
            "quotation_no",
            "revision_number",
            "quotation_date",
            "status",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at"
        ]


class InquiryQuotationSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    inquiry_quotation_details = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    inquiry_number = serializers.SerializerMethodField()

    class Meta:
        model = InquiryQuotation
        fields = [
            "id",
            "inquiry",
            "inquiry_number",
            "customer_name",
            "quotation_no",
            "revision_number",
            "quotation_date",
            "terms_and_condition",
            "status",
            "remarks",
            "converted_date",
            "inquiry_quotation_details",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
        ]
        read_only_fields = ["quotation_date", "quotation_no", "revision_number", "converted_date"]

    def get_customer_name(self, obj):
        if obj.inquiry:
            return obj.inquiry.customer_name
        return None

    def get_inquiry_number(self, obj):
        if obj.inquiry:
            return obj.inquiry.inquiry_number
        return None

    def get_inquiry_quotation_details(self, obj):
        inquiry_quotation_details = (
            obj.inquiry_quotation_details.filter(deleted=False)
            .select_related("alloy", "temper")
            .prefetch_related("surface_finish")
        )
        return InquiryQuotationDetailSerializer(
            inquiry_quotation_details, many=True
        ).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret["status"] = instance.status

        inquiry_quotation_details = InquiryQuotationDetail.objects.filter(
            inquiry_quotation=instance, deleted=0
        )
        inquiry_quotation_data = InquiryQuotationDetailSerializer(
            inquiry_quotation_details.order_by("id"), many=True, context=self.context
        ).data

        total_net_weight = Decimal(0)
        total_basic_amount = Decimal(0)
        total_gst_amount = Decimal(0)

        for detail in inquiry_quotation_details:
            net_weight = Decimal(detail.net_weight or 0)
            price_per_kg = round(Decimal(detail.price_per_kg or 0), 2)
            quantity = detail.quantity or 0
            conversion = round(Decimal(detail.conversion or 0), 2) * quantity
            packing_cost = round(Decimal(detail.packing_cost or 0), 2) * quantity
            total_rate = (price_per_kg + detail.conversion + (detail.packing_cost * detail.quantity))
            total_net_weight += net_weight
            cutting_price = round(Decimal(detail.cutting_price or 0), 2) * quantity
            machining_price = round(Decimal(detail.machining_price or 0), 2) * quantity
            deburring_price = round(Decimal(detail.deburring_price or 0), 2) * quantity
            anodising_price = round(Decimal(detail.anodising_price or 0), 2) * quantity
            powder_coating_price = (
                round(Decimal(detail.powder_coating_price or 0), 2) * quantity
            )
            pvdf_price = round(Decimal(detail.pvdf_price or 0), 2) * quantity

            total_basic_amount_detail = (price_per_kg * quantity) + conversion
            total_basic_amount_detail += packing_cost

            additional_prices_total = (
                cutting_price
                + machining_price
                + deburring_price
                + anodising_price
                + powder_coating_price
                + pvdf_price
            )

            total_basic_amount_detail += additional_prices_total
            total_basic_amount += total_basic_amount_detail

            gst_percentage = Decimal(18)

            gst_rate_detail = (
                gst_percentage / Decimal(100)
            ) * total_basic_amount_detail

            gst_rate_detail = round(gst_rate_detail, 2)
            total_gst_amount += gst_rate_detail

            total_amount_detail = total_basic_amount_detail + gst_rate_detail

            for data in inquiry_quotation_data:
                if data["id"] == detail.id:
                    data["net_weight"] = format(net_weight, ".2f")
                    data["total_rate"] = round(total_rate, 2)
                    data["total_basic_amount"] = round(total_basic_amount_detail, 2)
                    data["gst_rate"] = round(gst_rate_detail, 2)
                    data["total_amount"] = round(total_amount_detail, 2)
                    data["surface_finish_prices_total"] = round(
                        additional_prices_total, 2
                    )

                    surface_finishes = detail.surface_finish.all()
                    if surface_finishes:
                        data["surface_finish"] = [sf.id for sf in surface_finishes]
                    else:
                        data["surface_finish"] = []
        ret["inquiry_quotation_details"] = inquiry_quotation_data
        ret["total_net_weight"] = round(total_net_weight, 2)
        ret["total_basic_amount"] = round(total_basic_amount, 2)
        ret["total_gst_amount"] = round(total_gst_amount, 2)
        ret["total_amount"] = round(total_basic_amount + total_gst_amount, 2)

        if not inquiry_quotation_details:
            inquiry_quotation_details = [
                {
                    "id": None,
                    "inquiry_quotation": None,
                    "section_no": None,
                    "alloy": None,
                    "temper": None,
                    "length": None,
                    "price_per_kg": None,
                    "conversion": None,
                    "packing_cost": None,
                    "net_weight": None,
                    "surface_finish": None,
                    "out_source": None,
                    "cutting": None,
                    "machining": None,
                    "deburring": None,
                    "cutting_price": None,
                    "machining_price": None,
                    "deburring_price": None,
                    "anodising": None,
                    "powder_coating": None,
                    "pvdf": None,
                    "anodising_price": None,
                    "anodising_description": None,
                    "powder_coating_price": None,
                    "powder_coating_description": None,
                    "pvdf_price": None,
                    "pvdf_description": None,
                }
            ]

        price_fields = [
            "cutting_price",
            "machining_price",
            "deburring_price",
            "anodising_price",
            "powder_coating_price",
            "pvdf_price",
            "packing_cost",
            "price_per_kg",
            "conversion",
            "total_basic_amount",
            "gst_rate",
            "total_amount",
        ]

        for field in [
            "total_basic_amount",
            "total_gst_amount",
            "total_amount",
            "total_net_weight",
            "gst_rate",
        ]:
            if ret.get(field) not in [None, ""]:
                ret[field] = f"{Decimal(ret[field]):.2f}"

        return ret
