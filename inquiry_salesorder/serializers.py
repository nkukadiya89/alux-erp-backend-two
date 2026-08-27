from decimal import ROUND_HALF_UP, Decimal
from inquiry.serializers import TrimmedDecimalField
from rest_framework import serializers
from common.models import JobWorkType, PackingMode
from common.serializers import BaseModelSerializer
from customer.models import Customer
from customer.sort_serializers import CustomerBillToSerializer, CustomerShipToSerializer
from die.models import Die
from inquiry.serializers import AlloySerializer, JobWorkTypeSerializer, TemperSerializer
from inquiry.models import Inquiry
from inquiry_salesorder.models import InquirySalesOrder, InquirySalesOrderDetail
from product.models import Alloy, Temper
from user.serializers import UserQuickSerializer
from django.contrib.auth import get_user_model
from num2words import num2words

User = get_user_model()


class PackingModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackingMode
        fields = ["id", "name"]


class InquirySalesOrderDetailCreateSerializer(serializers.ModelSerializer):
    alloy = serializers.PrimaryKeyRelatedField(
        queryset=Alloy.objects.all(), required=False, allow_null=True
    )
    temper = serializers.PrimaryKeyRelatedField(
        queryset=Temper.objects.all(), required=False, allow_null=True
    )
    surface_finish = serializers.PrimaryKeyRelatedField(
        queryset=JobWorkType.objects.all(), required=False, allow_null=True, many=True
    )
    section_no = serializers.PrimaryKeyRelatedField(
        queryset=Die.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = InquirySalesOrderDetail
        fields = [
            "alloy",
            "temper",
            "length",
            "pieces",
            "surface_finish",
            "section_no",
            "nalco_rate",
            "modify_nalco_rate",
            "net_weight",
            "max_weight",
            "min_weight",
            "nalco_rate_change_reason",
            "conversion",
            "packing_cost",
            "customer_reference_number",
            "out_source",
            "cutting",
            "machining",
            "deburring",
            "salesorder_type",
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


class DieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Die
        fields = ["id", "die_number", "wt_kg_p_mt", "die_diagram", "description"]


class InquirySalesOrderDetailSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    alloy_detail = AlloySerializer(source="alloy", read_only=True)
    temper_detail = TemperSerializer(source="temper", read_only=True)
    surface_finish_detail = JobWorkTypeSerializer(
        source="surface_finish", read_only=True, many=True
    )
    section_detail = DieSerializer(source="section_no", read_only=True)
    length = TrimmedDecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = InquirySalesOrderDetail
        fields = [
            "id",
            "inquiry_salesorder",
            "alloy",
            "alloy_detail",
            "temper",
            "temper_detail",
            "section_detail",
            "surface_finish",
            "surface_finish_detail",
            "length",
            "pieces",
            "net_weight",
            "salesorder_type",
            "nalco_rate",
            "modify_nalco_rate",
            "nalco_rate_change_reason",
            "conversion",
            "packing_cost",
            "customer_reference_number",
            "price_per_kg",
            "packing_cost",
            "max_weight",
            "min_weight",
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

    def _get_quotation_detail(self, obj):
        if not obj.inquiry_salesorder or not obj.inquiry_salesorder.inquiry:
            return None

        inquiry = obj.inquiry_salesorder.inquiry

        quotation = (
            inquiry.inquiry_quotations.filter(deleted=False)
            .order_by("-created_at")
            .first()
        )
        if not quotation:
            return None

        if obj.section_no:
            quotation_detail = quotation.inquiry_quotation_details.filter(
                deleted=False, section_no=obj.section_no
            ).first()
            if quotation_detail:
                return quotation_detail

        if obj.alloy and obj.temper:
            quotation_detail = quotation.inquiry_quotation_details.filter(
                deleted=False, alloy=obj.alloy, temper=obj.temper
            ).first()
            if quotation_detail:
                return quotation_detail

        return quotation.inquiry_quotation_details.filter(deleted=False).first()


class InquirySalesOrderCreateSerializer(serializers.ModelSerializer):
    inquiry_salesorder_details = InquirySalesOrderDetailCreateSerializer(
        many=True, required=False
    )
    inquiry = serializers.PrimaryKeyRelatedField(
        queryset=Inquiry.objects.all(), required=False, allow_null=True
    )
    packing_mode = serializers.PrimaryKeyRelatedField(
        queryset=PackingMode.objects.all(), required=False, many=True
    )
    bill_to = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    ship_to = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    approved_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = InquirySalesOrder
        fields = [
            "id",
            "inquiry",
            "bill_to",
            "ship_to",
            "sales_order_no",
            "delivery_date",
            "order_type",
            "approved_by",
            "approved_at",
            "approval_reason",
            "purchase_order_no",
            "purchase_order_date",
            "project_name",
            "tolerance",
            "nalco_type",
            "packing_mode",
            "workorder_converted_date",
            "status",
            "remarks",
            "purchase_order_copy",
            "terms_and_condition",
            "inquiry_salesorder_details",
        ]

    def create(self, validated_data):
        packing_mode_data = validated_data.pop("packing_mode", [])
        inquiry_salesorder_details_data = validated_data.pop(
            "inquiry_salesorder_details", []
        )

        inquiry_salesorder = InquirySalesOrder.objects.create(**validated_data)

        if packing_mode_data:
            inquiry_salesorder.packing_mode.set(packing_mode_data)

        self.context["inquiry_salesorder_details_data"] = (
            inquiry_salesorder_details_data
        )
        return inquiry_salesorder


class InquirySalesOrderListSerializer(BaseModelSerializer):
    bill_to_name = serializers.CharField(source="bill_to.customer_name", read_only=True)
    workorder = serializers.CharField(
        source="workorder_inquiry_salesorder.order_no",
        read_only=True
    )
    workorder_status = serializers.CharField(
        source="workorder_inquiry_salesorder.status",
        read_only=True
    )
    class Meta(BaseModelSerializer.Meta):
        model = InquirySalesOrder
        fields = BaseModelSerializer.Meta.fields + [
            "sales_order_no",
            "order_date",
            "purchase_order_no",
            "purchase_order_date",
            "workorder",
            "approved_at",
            "approval_reason",
            "bill_to_name",
            "workorder_converted_date",
            "status",
            "workorder_status",
        ]

class InquirySalesOrderSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    inquiry_salesorder_details = serializers.SerializerMethodField()
    bill_to_name = CustomerBillToSerializer(source="bill_to", read_only=True)
    ship_to_name = CustomerShipToSerializer(source="ship_to", read_only=True)
    inquiry_number = serializers.SerializerMethodField()
    quotation_no = serializers.SerializerMethodField()
    packing_mode_detail = PackingModeSerializer(
        source="packing_mode", read_only=True, many=True
    )
    bill_to = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    ship_to = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    approved_by_detail = serializers.SerializerMethodField()

    class Meta:
        model = InquirySalesOrder
        fields = [
            "id",
            "inquiry",
            "inquiry_number",
            "bill_to",
            "bill_to_name",
            "ship_to_name",
            "ship_to",
            "quotation_no",
            "sales_order_no",
            "order_date",
            "order_type",
            "delivery_date",
            "purchase_order_no",
            "purchase_order_date",
            "project_name",
            "tolerance",
            "nalco_type",
            "packing_mode",
            "packing_mode_detail",
            "status",
            "workorder_converted_date",
            "remarks",
            "purchase_order_copy",
            "inquiry_salesorder_details",
            "terms_and_condition",
            "created_by",
            "updated_by",
            "approved_by",
            "approved_by_detail",
            "approved_at",
            "approval_reason",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
        ]
        read_only_fields = ["order_date", "sales_order_no"]

    def get_approved_by_detail(self, obj):
        if obj.approved_by:
            return {
                "id": obj.approved_by.id,
                "first_name": obj.approved_by.first_name,
                "last_name": obj.approved_by.last_name,
            }
        return None

    def get_inquiry_number(self, obj):
        if obj.inquiry:
            return obj.inquiry.inquiry_number
        return None

    def get_inquiry_salesorder_details(self, obj):
        inquiry_salesorder_details = (
            obj.inquiry_salesorder_details.filter(deleted=False)
            .select_related("alloy", "temper")
            .prefetch_related("surface_finish")
        )
        return InquirySalesOrderDetailSerializer(
            inquiry_salesorder_details, many=True
        ).data

    def get_quotation_no(self, obj):
        if obj.inquiry:
            quotation = (
                obj.inquiry.inquiry_quotations.filter(deleted=False)
                .order_by("-created_at")
                .first()
            )
            if quotation:
                return quotation.quotation_no
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret["status"] = instance.status

        inquiry_salesorder_details = InquirySalesOrderDetail.objects.filter(
            inquiry_salesorder=instance, deleted=False
        )
        inquiry_salesorder_data = InquirySalesOrderDetailSerializer(
            inquiry_salesorder_details.order_by("id"), many=True, context=self.context
        ).data

        customer = instance.bill_to
        applicable_gst = customer.applicable_gst if customer else None
        is_igst = applicable_gst == "IGST"

        total_net_weight = Decimal(0)
        total_basic_amount = Decimal(0)
        total_gst_amount = Decimal(0)
        sub_total_detail = Decimal(0)
        total_sub_total = Decimal(0)
        total_igst_amount = Decimal(0)
        total_sgst_amount = Decimal(0)
        total_cgst_amount = Decimal(0)
        total_pieces = 0
        total_packing_cost = Decimal(0)

        for detail in inquiry_salesorder_details:
            quotation_detail = None
            if detail.inquiry_salesorder and detail.inquiry_salesorder.inquiry:
                inquiry = detail.inquiry_salesorder.inquiry
                quotation = (
                    inquiry.inquiry_quotations.filter(deleted=False)
                    .order_by("-created_at")
                    .first()
                )
                if quotation:
                    section_no = None
                    if detail.alloy and detail.temper:
                        quotation_query = quotation.inquiry_quotation_details.filter(
                            deleted=False, alloy=detail.alloy, temper=detail.temper
                        )
                        if detail.length:
                            quotation_query = quotation_query.filter(
                                length=detail.length
                            )
                        quotation_detail = quotation_query.first()
                        if quotation_detail and quotation_detail.section_no:
                            section_no = quotation_detail.section_no

                    if not section_no and detail.alloy and detail.temper:
                        inquiry_query = inquiry.inquiry_details.filter(
                            deleted=False, alloy=detail.alloy, temper=detail.temper
                        )
                        if detail.length:
                            inquiry_query = inquiry_query.filter(length=detail.length)
                        inquiry_detail = inquiry_query.first()
                        if inquiry_detail:
                            section_no = inquiry_detail.section_no
                            if section_no:
                                quotation_detail = (
                                    quotation.inquiry_quotation_details.filter(
                                        deleted=False, section_no=section_no
                                    ).first()
                                )

                    if not quotation_detail and detail.alloy and detail.temper:
                        quotation_detail = quotation.inquiry_quotation_details.filter(
                            deleted=False, alloy=detail.alloy, temper=detail.temper
                        ).first()
                        if quotation_detail and quotation_detail.section_no:
                            section_no = quotation_detail.section_no

                    if not quotation_detail and detail.alloy and detail.temper:
                        inquiry_detail = inquiry.inquiry_details.filter(
                            deleted=False, alloy=detail.alloy, temper=detail.temper
                        ).first()
                        if inquiry_detail:
                            section_no = inquiry_detail.section_no
                            if section_no:
                                quotation_detail = (
                                    quotation.inquiry_quotation_details.filter(
                                        deleted=False, section_no=section_no
                                    ).first()
                                )

                    if not section_no:
                        inquiry_detail = (
                            inquiry.inquiry_details.filter(deleted=False)
                            .order_by("section_no")
                            .first()
                        )
                        if inquiry_detail:
                            section_no = inquiry_detail.section_no
                            if section_no:
                                quotation_detail = (
                                    quotation.inquiry_quotation_details.filter(
                                        deleted=False, section_no=section_no
                                    ).first()
                                )

                    if not quotation_detail:
                        quotation_detail = quotation.inquiry_quotation_details.filter(
                            deleted=False
                        ).first()

            net_weight = Decimal(str(detail.net_weight or 0))
            price_per_kg = round(Decimal(detail.price_per_kg or 0), 2)
            conversion = round(Decimal(detail.conversion or 0), 2)
            packing_cost = round(Decimal(detail.packing_cost or 0), 2)

            cutting_price = round(Decimal(detail.cutting_price or 0), 2)
            machining_price = round(Decimal(detail.machining_price or 0), 2)
            deburring_price = round(Decimal(detail.deburring_price or 0), 2)
            anodising_price = round(Decimal(detail.anodising_price or 0), 2)
            powder_coating_price = round(Decimal(detail.powder_coating_price or 0), 2)
            pvdf_price = round(Decimal(detail.pvdf_price or 0), 2)

            cutting_price = round(Decimal(cutting_price or 0) * net_weight, 2)
            machining_price = round(Decimal(machining_price or 0) * net_weight, 2)
            deburring_price = round(Decimal(deburring_price or 0) * net_weight, 2)
            anodising_price = round(Decimal(anodising_price or 0) * net_weight, 2)
            powder_coating_price = round(
                Decimal(powder_coating_price or 0) * net_weight, 2
            )
            pvdf_price = round(Decimal(pvdf_price or 0) * net_weight, 2)
            total_basic_amount_detail = price_per_kg * net_weight
            total_basic_amount_detail += conversion * net_weight
            sub_total_detail = total_basic_amount_detail + (packing_cost * net_weight)

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

            half_gst = (Decimal(9) / Decimal(100)) * sub_total_detail
            half_gst = round(half_gst, 2)

            if is_igst:
                gst_rate_detail = half_gst * 2
                igst_rate_detail = gst_rate_detail
                sgst_rate_detail = Decimal(0)
                cgst_rate_detail = Decimal(0)
            else:
                gst_rate_detail = Decimal(0)
                igst_rate_detail = Decimal(0)
                sgst_rate_detail = half_gst
                cgst_rate_detail = half_gst

            total_gst_amount += igst_rate_detail + sgst_rate_detail + cgst_rate_detail
            total_igst_amount += igst_rate_detail
            total_sgst_amount += sgst_rate_detail
            total_cgst_amount += cgst_rate_detail
            total_sub_total += sub_total_detail

            total_amount_detail = (
                sub_total_detail + gst_rate_detail + sgst_rate_detail + cgst_rate_detail
            )

            total_pieces += detail.pieces or 0
            total_net_weight += Decimal(detail.net_weight or 0)
            total_packing_cost += packing_cost * net_weight

            for data in inquiry_salesorder_data:
                if data["id"] == detail.id:
                    data["net_weight"] = net_weight
                    data["total_basic_amount"] = round(total_basic_amount_detail, 2)
                    data["sub_total"] = round(sub_total_detail, 2)
                    data["gst_rate"] = round(gst_rate_detail, 2)
                    data["igst_rate"] = round(igst_rate_detail, 2)
                    data["sgst_rate"] = round(sgst_rate_detail, 2)
                    data["cgst_rate"] = round(cgst_rate_detail, 2)
                    data["total_amount"] = round(total_amount_detail, 2)
                    data["surface_finish_prices_total"] = round(
                        additional_prices_total, 2
                    )

                    surface_finishes = detail.surface_finish.all()
                    if surface_finishes:
                        data["surface_finish"] = [sf.id for sf in surface_finishes]
                    else:
                        data["surface_finish"] = []

        if not inquiry_salesorder_details:
            inquiry_salesorder_data = [
                {
                    "id": None,
                    "inquiry_salesorder": None,
                    "section_no": None,
                    "alloy": None,
                    "temper": None,
                    "length": None,
                    "nalco_rate": None,
                    "modify_nalco_rate": None,
                    "nalco_rate_change_reason": None,
                    "conversion": None,
                    "packing_cost": None,
                    "customer_reference_number": None,
                    "price_per_kg": None,
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

        total_payable = Decimal("0.00")
        total_payable = total_sub_total + total_gst_amount

        final_amount = total_payable.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        round_off = (final_amount - total_payable).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        ret["inquiry_salesorder_details"] = inquiry_salesorder_data
        ret["total_net_weight"] = f"{total_net_weight :.3f}"
        ret["total_basic_amount"] = round(total_basic_amount, 2)
        ret["sub_total"] = f"{total_sub_total :.2f}"
        ret["total_gst_amount"] = round(total_gst_amount, 2)
        ret["total_igst_amount"] = round(total_igst_amount, 2)
        ret["total_sgst_amount"] = round(total_sgst_amount, 2)
        ret["total_cgst_amount"] = round(total_cgst_amount, 2)
        ret["applicable_gst"] = applicable_gst
        ret["total_payble_amount"] = f"{total_payable :.2f}" 
        ret["round_off"] = f"{round_off :+.2f}"
        ret["total_amount"] = f"{final_amount :.2f}"
        ret["total_pieces"] = total_pieces
        ret["total_packing_cost"] = round(total_packing_cost, 2)
        ret["total_amount_words"] = (num2words(int(total_payable), lang="en_IN").replace(",", "").replace(" and ", " ").replace("-", " ").title() + " Rupees Only").upper()

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
            "sub_total",
            "igst_rate",
            "sgst_rate",
            "cgst_rate",
            "total_amount",
        ]

        for detail_data in ret.get("inquiry_salesorder_details", []):
            for field in price_fields:
                if detail_data.get(field) not in [None, ""]:
                    detail_data[field] = f"{Decimal(detail_data[field]):.2f}"

                if detail_data.get("net_weight") not in [None, ""]:
                    detail_data["net_weight"] = (
                        f"{Decimal(detail_data['net_weight']):.3f}"
                    )

        for field in [
            "total_basic_amount",
            "total_gst_amount",
            "total_igst_amount",
            "total_sgst_amount",
            "total_cgst_amount",
            "total_amount",
            "total_sub_total",
            "total_packing_cost",
            "gst_rate",
        ]:
            if ret.get(field) not in [None, ""]:
                ret[field] = f"{Decimal(ret[field]):.2f}"

        return ret


class InquirySalesOrderArchiveListSerializer(serializers.ModelSerializer):
    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    deleted_by = UserQuickSerializer(read_only=True)
    packing_mode = serializers.PrimaryKeyRelatedField(
        queryset=PackingMode.objects.all(), required=False, many=True
    )

    class Meta:
        model = InquirySalesOrder
        fields = [
            "id",
            "inquiry",
            "order_date",
            "sales_order_no",
            "delivery_date",
            "purchase_order_no",
            "purchase_order_date",
            "project_name",
            "tolerance",
            "nalco_type",
            "bill_to",
            "ship_to",
            "packing_mode",
            "remarks",
            "status",
            "purchase_order_copy",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted",
        ]
        read_only_fields = ["order_date", "sales_order_no"]
