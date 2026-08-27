import json
from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import OuterRef, Subquery
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die.models import Die
from inquiry_quotation.models import InquiryQuotation, InquiryQuotationDetail
from inquiry_quotation.serializers import (
    InquiryQuotationCreateSerializer,
    InquiryQuotationDetailCreateSerializer,
    InquiryQuotationDetailSerializer,
    InquiryQuotationListSerializer,
    InquiryQuotationSerializer,
)
from inquiry_salesorder.serializers import (
    InquirySalesOrderCreateSerializer,
    InquirySalesOrderDetailCreateSerializer,
)
from inquiry_salesorder.views import _create_workorder_from_salesorder
from utils.generate_number import (
    generate_inquiry_quotation_number,
    generate_sales_order_number,
)
from utils.log_activity import clean_payload, log_user_activity


class InquiryQuotationViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = InquiryQuotation.objects.all()
    serializer_class = InquiryQuotationSerializer
    list_serializer_class = InquiryQuotationListSerializer

    def get_queryset(self):
        latest_revision = (
            InquiryQuotation.objects
            .filter(quotation_no=OuterRef("quotation_no"), deleted=False)
            .order_by("-revision_number")
            .values("id")[:1]
        )
        qs = (
                InquiryQuotation.objects.filter(id=Subquery(latest_revision)).select_related(
                    "inquiry",
                    "created_by",
                    "updated_by",
                    "deleted_by",
                ).order_by("-id")
            )
        return qs

    search_fields = [
        "quotation_no",
        "status",
        "inquiry__inquiry_number",
        "inquiry__customer_name",
        "inquiry__contact_persons",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]
    ordering_fields = [
        "quotation_no",
        "quotation_date",
        "status",
        "created_at",
        "updated_at",
        "converted_date",
        "inquiry__inquiry_number",
        "inquiry__customer_name",
    ]

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        quotation = self.get_object()

        revisions = (
            InquiryQuotation.objects
            .filter(quotation_no=quotation.quotation_no, deleted=False)
            .exclude(id=quotation.id)
            .order_by("-revision_number")
        )

        serializer = InquiryQuotationListSerializer(revisions, many=True)

        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = InquiryQuotation.objects.get(
            pk=kwargs["pk"],
            deleted=False
        )

        serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            quotation_details_data = request.data.pop("quotation_details", [])

            serializer = InquiryQuotationCreateSerializer(
                data=request.data, context={"request": request}
            )

            if serializer.is_valid():
                with transaction.atomic():
                    quotation_no = generate_inquiry_quotation_number()
                    inquiry_quotation = serializer.save(
                        quotation_no=quotation_no,
                        revision_number=0,
                        created_by=request.user,
                        updated_by=request.user,
                    )

                    for detail_data in quotation_details_data:
                        surface_finish_ids = detail_data.pop("surface_finish", [])

                        detail_serializer = InquiryQuotationDetailCreateSerializer(
                            data=detail_data
                        )
                        if detail_serializer.is_valid():
                            quotation_detail = detail_serializer.save(
                                inquiry_quotation=inquiry_quotation,
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            if surface_finish_ids:
                                quotation_detail.surface_finish.set(surface_finish_ids)
                        else:
                            return Response(
                                {
                                    "success": False,
                                    "message": "Invalid quotation detail data.",
                                    "errors": detail_serializer.errors,
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="CREATE",
                        module_name="InquiryQuotation",
                        description=f"Created InquiryQuotation {quotation_no}",
                        request=request,
                        payload=payload,
                    )

                    response_serializer = InquiryQuotationSerializer(inquiry_quotation)
                    return Response(
                        {
                            "success": True,
                            "message": "Inquiry quotation created successfully.",
                            "data": response_serializer.data,
                        },
                        status=status.HTTP_201_CREATED,
                    )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid data provided.",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating inquiry quotation: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def values_are_different(self, old_value, new_value):
        from decimal import Decimal, InvalidOperation
        if old_value is None and new_value in [None, ""]:
            return False

        if new_value is None and old_value in [None, ""]:
            return False

        try:
            return Decimal(str(old_value or 0)) != Decimal(str(new_value or 0))
        except (InvalidOperation, TypeError):
            return str(old_value or "").strip() != str(new_value or "").strip()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            incoming_details = request.data.pop("quotation_details", None)
            fields_to_check = [
                "terms_and_condition",
                "remarks"
            ]
            has_field_change = False
            for f in fields_to_check:
                if f in request.data:
                    incoming_val = request.data.get(f)
                    current_val = getattr(instance, f)
                    if str(incoming_val) != str(current_val):
                        has_field_change = True
                        break

            has_details_change = False
            if isinstance(incoming_details, list):
                existing_details_qs = (
                    instance.inquiry_quotation_details.filter(deleted=False)
                    .select_related("alloy", "temper")
                    .prefetch_related("surface_finish")
                )
                existing_count = existing_details_qs.count()

                if len(incoming_details) != existing_count:
                    has_details_change = True
                else:
                    existing_by_id = {d.id: d for d in existing_details_qs}
                    detail_fields = [
                        "price_per_kg",
                        "conversion",
                        "packing_cost",
                        "quantity",
                    ]

                    for item in incoming_details:
                        item_id = item.get("id")
                        if not item_id:
                            has_details_change = True
                            break
                        existing = existing_by_id.get(item_id)
                        if not existing:
                            has_details_change = True
                            break

                        for key in detail_fields:
                            if key in item:
                                incoming_val = item.get(key)
                                current_val = getattr(existing, key)
                                if self.values_are_different(current_val, incoming_val):
                                    has_details_change = True
                                    break
                        if has_details_change:
                            break

                        if "surface_finish" in item:
                            incoming_sf = sorted(
                                [int(x) for x in (item.get("surface_finish") or [])]
                            )
                            current_sf = sorted(
                                list(
                                    existing.surface_finish.values_list("id", flat=True)
                                )
                            )
                            if incoming_sf != current_sf:
                                has_details_change = True
                                break

            if (
                (incoming_details is None)
                or (isinstance(incoming_details, list) and not has_details_change)
            ) and not has_field_change:
                serializer = self.get_serializer(instance)
                return Response(
                    {
                        "success": True,
                        "message": "No changes detected; nothing updated.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            base = instance.quotation_no

            with transaction.atomic():
                siblings = (
                    InquiryQuotation.objects.select_for_update()
                    .filter(
                        quotation_no=base,
                        inquiry=instance.inquiry,
                        deleted=False,
                    )
                )
                max_revision = siblings.aggregate(
                    max_rev=models.Max("revision_number")
                )["max_rev"] or 0

                if max_revision >= 3:
                    return Response(
                        {
                            "success": False,
                            "message": "Quotation Revised limit is reached.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if max_revision == 0:
                    siblings.filter(revision_number=0).update(revision_number=1)
                    new_revision = 2
                else:
                    new_revision = max_revision + 1

                new_q = InquiryQuotation.objects.create(
                    inquiry=instance.inquiry,
                    quotation_no=base,
                    revision_number=new_revision,
                    quotation_date=instance.quotation_date,
                    terms_and_condition=request.data.get(
                        "terms_and_condition", instance.terms_and_condition
                    ),
                    status=request.data.get("status", instance.status),
                    remarks=request.data.get("remarks", instance.remarks),
                    converted_date=None,
                    created_by=request.user,
                    updated_by=request.user,
                )

                if incoming_details is not None:
                    existing_details_map = {
                        d.id: d
                        for d in instance.inquiry_quotation_details.filter(
                            deleted=False
                        )
                    }
                    for detail_data in incoming_details or []:
                        existing_detail = None
                        detail_id = detail_data.get("id")
                        if detail_id:
                            existing_detail = existing_details_map.get(detail_id)

                        if existing_detail:
                            backfill_fields = [
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
                            ]

                            for f in backfill_fields:
                                if f not in detail_data:
                                    val = getattr(existing_detail, f)
                                    if f in ["alloy", "temper"]:
                                        val = val.id if val else None
                                    detail_data[f] = val

                            if "surface_finish" not in detail_data:
                                detail_data["surface_finish"] = list(
                                    existing_detail.surface_finish.values_list(
                                        "id", flat=True
                                    )
                                )

                        surface_finish_ids = detail_data.pop("surface_finish", [])
                        detail_serializer = InquiryQuotationDetailCreateSerializer(
                            data=detail_data
                        )
                        if not detail_serializer.is_valid():
                            return Response(
                                {
                                    "success": False,
                                    "message": "Invalid quotation detail data.",
                                    "errors": detail_serializer.errors,
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        new_detail = detail_serializer.save(
                            inquiry_quotation=new_q,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                        if surface_finish_ids:
                            new_detail.surface_finish.set(surface_finish_ids)
                else:
                    for d in instance.inquiry_quotation_details.filter(
                        deleted=False
                    ).all():
                        new_detail = InquiryQuotationDetail.objects.create(
                            inquiry_quotation=new_q,
                            section_no=d.section_no,
                            alloy=d.alloy,
                            temper=d.temper,
                            length=d.length,
                            price_per_kg=d.price_per_kg,
                            conversion=d.conversion,
                            packing_cost=d.packing_cost,
                            net_weight=d.net_weight,
                            quantity=d.quantity,
                            out_source=d.out_source,
                            cutting=d.cutting,
                            machining=d.machining,
                            deburring=d.deburring,
                            cutting_price=d.cutting_price,
                            machining_price=d.machining_price,
                            deburring_price=d.deburring_price,
                            anodising=d.anodising,
                            powder_coating=d.powder_coating,
                            pvdf=d.pvdf,
                            anodising_price=d.anodising_price,
                            anodising_description=d.anodising_description,
                            powder_coating_price=d.powder_coating_price,
                            powder_coating_description=d.powder_coating_description,
                            pvdf_price=d.pvdf_price,
                            pvdf_description=d.pvdf_description,
                            laser_marking_price=d.laser_marking_price,
                            laser_marking_description=d.laser_marking_description,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                        if d.surface_finish.exists():
                            new_detail.surface_finish.set(
                                list(d.surface_finish.values_list("id", flat=True))
                            )

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="InquiryQuotation",
                    description=f"Created revision {new_revision} for InquiryQuotation {base}",
                    request=request,
                    payload=payload,
                )

                response_serializer = InquiryQuotationSerializer(new_q)
                return Response(
                    {
                        "success": True,
                        "message": "Inquiry quotation updated (new version created) successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating inquiry quotation: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="convert-to-salesorder")
    def convert_to_salesorder(self, request, pk=None):
        try:
            try:
                packing_mode_ids = request.data.get("packing_mode", [])
                inquiry_quotation = InquiryQuotation.objects.select_related(
                    "inquiry"
                ).get(id=pk, deleted=False)
            except InquiryQuotation.DoesNotExist:
                return Response(
                    {"message": "Inquiry quotation not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if "data" in request.data:
                data_str = request.data.get("data")
                if isinstance(data_str, str):
                    try:
                        parsed_data = json.loads(data_str)
                    except json.JSONDecodeError as e:
                        return Response(
                            {"message": f"Invalid JSON: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    parsed_data = data_str

                quotation_details_data = parsed_data.get("sales_order_details", [])
                sales_order_data = {
                    "purchase_order_no": parsed_data.get("purchase_order_no"),
                    "purchase_order_date": parsed_data.get("purchase_order_date"),
                    "delivery_date": parsed_data.get("delivery_date"),
                    "project_name": parsed_data.get("project_name"),
                    "tolerance": parsed_data.get("tolerance"),
                    "nalco_type": parsed_data.get("nalco_type"),
                    "packing_mode": parsed_data.get("packing_mode", []),
                    "remarks": parsed_data.get("remarks", ""),
                    "bill_to": parsed_data.get("customer"),
                    "approved_by": parsed_data.get("approved_by"),
                    "terms_and_condition": parsed_data.get("terms_and_condition"),
                }
            else:
                quotation_details_data = request.data.get("salesorder_details", [])
                sales_order_data = {
                    "purchase_order_no": request.data.get("purchase_order_no"),
                    "purchase_order_date": request.data.get("purchase_order_date"),
                    "delivery_date": request.data.get("delivery_date"),
                    "project_name": request.data.get("project_name"),
                    "tolerance": request.data.get("tolerance"),
                    "nalco_type": request.data.get("nalco_type"),
                    "packing_mode": request.data.get("packing_mode", []),
                    "remarks": request.data.get("remarks", ""),
                    "bill_to": request.data.get("customer"),
                    "approved_by": request.data.get("approved_by"),
                    "terms_and_condition": request.data.get("terms_and_condition"),
                }

            if not quotation_details_data:
                return Response(
                    {"sales_order_details": "This field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            section_ids = [
                item.get("section_no")
                for item in quotation_details_data
                if item.get("section_no")
            ]

            existing_ids = set(
                Die.objects.filter(id__in=section_ids).values_list("id", flat=True)
            )

            detail_errors = []

            for index, item in enumerate(quotation_details_data):
                section_no = item.get("section_no")

                if not section_no:
                    detail_errors.append(
                        {
                            "section_no": "section_no is required for each sales order detail"
                        }
                    )
                    continue

                if section_no not in existing_ids:
                    detail_errors.append(
                        {"section_no": f"section_no {section_no} does not exist"}
                    )

            sales_order_data["inquiry"] = inquiry_quotation.inquiry.id

            sales_order_serializer = InquirySalesOrderCreateSerializer(
                data=sales_order_data
            )

            main_errors = {}

            if not sales_order_serializer.is_valid():
                main_errors = sales_order_serializer.errors

            if main_errors or detail_errors:
                response_data = {}

                if main_errors:
                    response_data.update(main_errors)

                if detail_errors:
                    response_data["sales_order_details"] = detail_errors

                return Response(
                    {
                        "success": False,
                        "message": "Invalid sales order data",
                        "errors": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                sales_order_no = generate_sales_order_number()

                inquiry_salesorder = sales_order_serializer.save(
                    sales_order_no=sales_order_no,
                    created_by=request.user,
                    updated_by=request.user,
                )

                if packing_mode_ids:
                    inquiry_salesorder.packing_mode.set(packing_mode_ids)

                purchase_order_copy = request.FILES.get("purchase_order_copy")
                if purchase_order_copy:
                    inquiry_salesorder.upload_doc(
                        {"purchase_order_copy": purchase_order_copy}
                    )

                for item in quotation_details_data:
                    detail_data = {
                        "section_no": item.get("section_no"),
                        "alloy": item.get("alloy"),
                        "temper": item.get("temper"),
                        "length": item.get("length"),
                        "pieces": item.get("pieces"),
                        "net_weight": item.get("net_weight"),
                        "nalco_rate": item.get("nalco_rate"),
                        "modify_nalco_rate": item.get("modify_nalco_rate", False),
                        "nalco_rate_change_reason": item.get(
                            "nalco_rate_change_reason"
                        ),
                        "conversion": item.get("conversion"),
                        "packing_cost": item.get("packing_cost"),
                        "out_source": item.get("out_source", False),
                        "cutting": item.get("cutting", False),
                        "machining": item.get("machining", False),
                        "deburring": item.get("deburring", False),
                        "cutting_price": item.get("cutting_price"),
                        "machining_price": item.get("machining_price"),
                        "deburring_price": item.get("deburring_price"),
                        "anodising": item.get("anodising", False),
                        "powder_coating": item.get("powder_coating", False),
                        "pvdf": item.get("pvdf", False),
                        "anodising_price": item.get("anodising_price"),
                        "anodising_description": item.get("anodising_description"),
                        "powder_coating_price": item.get("powder_coating_price"),
                        "powder_coating_description": item.get(
                            "powder_coating_description"
                        ),
                        "pvdf_price": item.get("pvdf_price"),
                        "pvdf_description": item.get("pvdf_description"),
                        "laser_marking_price": item.get("laser_marking_price"),
                        "laser_marking_description": item.get(
                            "laser_marking_description"
                        ),
                    }

                    surface_finish_ids = item.get("surface_finish", [])

                    detail_serializer = InquirySalesOrderDetailCreateSerializer(
                        data=detail_data
                    )

                    if not detail_serializer.is_valid():
                        raise Exception(detail_serializer.errors)

                    detail_obj = detail_serializer.save(
                        inquiry_salesorder=inquiry_salesorder,
                        created_by=request.user,
                        updated_by=request.user,
                    )

                    if surface_finish_ids:
                        detail_obj.surface_finish.set(surface_finish_ids)

                inquiry_quotation.status = "SalesOrder"
                inquiry_quotation.converted_date = timezone.now().date()
                inquiry_quotation.updated_by = request.user
                inquiry_quotation.save()

                if inquiry_salesorder.nalco_type == "Variable":
                    _create_workorder_from_salesorder(inquiry_salesorder, request.user)

                inquiry = inquiry_quotation.inquiry
                inquiry.status = "SalesOrder"
                inquiry.updated_by = request.user
                inquiry.save()

            return Response(
                {
                    "success": True,
                    "message": "Inquiry quotation converted successfully",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InquiryQuotationDetailViewSet(BaseModelViewSet):
    queryset = InquiryQuotationDetail.objects.all()
    serializer_class = InquiryQuotationDetailSerializer

    search_fields = [
        "section_no",
        "inquiry_quotation__quotation_no",
        "inquiry_quotation__status",
        "inquiry_quotation__inquiry__inquiry_number",
        "inquiry_quotation__inquiry__customer_name",
        "alloy__name",
        "temper__name",
        "anodising_description",
        "powder_coating_description",
        "pvdf_description",
        "laser_marking_description",
        "created_by__first_name",
        "created_by__last_name",
        "created_by__email",
        "updated_by__first_name",
        "updated_by__last_name",
        "updated_by__email",
    ]
    ordering_fields = [
        "section_no",
        "created_at",
        "updated_at",
        "length",
        "price_per_kg",
        "inquiry_quotation__quotation_no",
        "alloy__name",
        "temper__name",
    ]

    def get_queryset(self):
        return (
            InquiryQuotationDetail.objects.filter(deleted=False)
            .select_related(
                "inquiry_quotation",
                "alloy",
                "temper",
                "created_by",
                "updated_by",
                "deleted_by",
            )
            .prefetch_related("surface_finish")
            .order_by("-id")
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            surface_finish_ids = request.data.pop("surface_finish", [])
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    quotation_detail = serializer.save(
                        created_by=request.user, updated_by=request.user
                    )

                    if surface_finish_ids:
                        quotation_detail.surface_finish.set(surface_finish_ids)

                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="CREATE",
                        module_name="InquiryQuotationDetail",
                        description=f"Created InquiryQuotationDetail",
                        request=request,
                        payload=payload,
                    )

                    response_serializer = self.get_serializer(quotation_detail)

                return Response(
                    {
                        "success": True,
                        "message": "Inquiry quotation detail created successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid data provided.",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating inquiry quotation detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            surface_finish_ids = request.data.pop("surface_finish", None)

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    quotation_detail = serializer.save(updated_by=request.user)

                    if surface_finish_ids is not None:
                        quotation_detail.surface_finish.set(surface_finish_ids)

                    quotation_detail.refresh_from_db()

                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="UPDATE",
                        module_name="InquiryQuotationDetail",
                        description=f"Updated InquiryQuotationDetail",
                        request=request,
                        payload=payload,
                    )

                    response_serializer = self.get_serializer(quotation_detail)

                return Response(
                    {
                        "success": True,
                        "message": "Inquiry quotation detail updated successfully.",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid data provided.",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating inquiry quotation detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
