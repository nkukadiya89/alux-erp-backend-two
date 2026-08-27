import json
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from decimal import Decimal
from utils.error_handling import custom_exception
from common.models import JobWorkType
from customer.models import Customer
from inquiry_salesorder.models import InquirySalesOrder, InquirySalesOrderDetail
from workorder.models import WorkOrder, WorkOrderDetail
from inquiry_salesorder.serializers import (
    InquirySalesOrderArchiveListSerializer,
    InquirySalesOrderCreateSerializer,
    InquirySalesOrderDetailCreateSerializer,
    InquirySalesOrderDetailSerializer,
    InquirySalesOrderListSerializer,
    InquirySalesOrderSerializer,
)
from utils.generate_number import derive_workorder_no_from_salesorder, generate_sales_order_number
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from common.master_views import BaseModelViewSet


def _update_workorder_from_salesorder(salesorder, user):
    """Sync WorkOrder and its Pending WorkOrderDetails from updated SalesOrder."""
    workorder = WorkOrder.objects.filter(salesorder=salesorder, deleted=False).first()
    if not workorder:
        return

    workorder.bill_to = salesorder.bill_to
    workorder.ship_to = salesorder.ship_to
    workorder.purchase_order_no = salesorder.purchase_order_no
    workorder.purchase_order_date = salesorder.purchase_order_date
    workorder.delivery_date = salesorder.delivery_date
    workorder.order_type = salesorder.order_type
    workorder.project_name = salesorder.project_name
    workorder.nalco_type = salesorder.nalco_type
    workorder.tolerance = salesorder.tolerance
    workorder.remarks = salesorder.remarks
    workorder.terms_and_condition = salesorder.terms_and_condition
    workorder.approved_by = salesorder.approved_by
    workorder.po_copy = salesorder.purchase_order_copy
    workorder.updated_by = user
    workorder.save()
    workorder.packing_mode.set(salesorder.packing_mode.all())

    for so_detail in salesorder.inquiry_salesorder_details.filter(deleted=False):
        wo_detail = WorkOrderDetail.objects.filter(
            salesorder_detail=so_detail, deleted=False, status="Pending"
        ).first()

        net_weight = so_detail.net_weight or Decimal(0)
        pieces = so_detail.pieces or 0

        if not wo_detail:
            wo_detail = WorkOrderDetail(
                workorder=workorder,
                salesorder_detail=so_detail,
                created_by=user,
            )

        wo_detail.die_profile = so_detail.section_no
        wo_detail.alloy = so_detail.alloy
        wo_detail.temper = so_detail.temper
        wo_detail.length = so_detail.length
        wo_detail.pieces = pieces
        wo_detail.net_weight = net_weight
        wo_detail.max_weight = so_detail.max_weight
        wo_detail.min_weight = so_detail.min_weight
        wo_detail.nalco_rate = so_detail.nalco_rate
        wo_detail.modify_nalco_rate = so_detail.modify_nalco_rate
        wo_detail.nalco_rate_change_reason = so_detail.nalco_rate_change_reason
        wo_detail.conversion = so_detail.conversion
        wo_detail.packing_cost = so_detail.packing_cost
        wo_detail.customer_reference_number = so_detail.customer_reference_number
        wo_detail.out_source = so_detail.out_source
        wo_detail.cutting = so_detail.cutting
        wo_detail.machining = so_detail.machining
        wo_detail.deburring = so_detail.deburring
        wo_detail.cutting_price = so_detail.cutting_price
        wo_detail.machining_price = so_detail.machining_price
        wo_detail.deburring_price = so_detail.deburring_price
        wo_detail.anodising = so_detail.anodising
        wo_detail.powder_coating = so_detail.powder_coating
        wo_detail.pvdf = so_detail.pvdf
        wo_detail.anodising_price = so_detail.anodising_price
        wo_detail.anodising_description = so_detail.anodising_description
        wo_detail.powder_coating_price = so_detail.powder_coating_price
        wo_detail.powder_coating_description = so_detail.powder_coating_description
        wo_detail.pvdf_price = so_detail.pvdf_price
        wo_detail.pvdf_description = so_detail.pvdf_description
        wo_detail.laser_marking_price = so_detail.laser_marking_price
        wo_detail.laser_marking_description = so_detail.laser_marking_description
        wo_detail.pending_weight = net_weight
        wo_detail.pending_pieces = pieces
        wo_detail.updated_by = user
        wo_detail.save()
        wo_detail.surface_finish.set(so_detail.surface_finish.all())

        from workorder.process_tracking import (
            ensure_item_process_track,
            sync_jobwork_stages_for_detail,
        )

        ensure_item_process_track(wo_detail, user=user, mark_created=True)
        sync_jobwork_stages_for_detail(wo_detail, user=user)


def _create_workorder_from_salesorder(salesorder, user):
    """Create a WorkOrder and WorkOrderDetails from a SalesOrder."""
    workorder = WorkOrder.objects.create(
        order_no=derive_workorder_no_from_salesorder(salesorder.sales_order_no),
        order_date=timezone.now().date(),
        salesorder=salesorder,
        bill_to=salesorder.bill_to,
        ship_to=salesorder.ship_to,
        purchase_order_no=salesorder.purchase_order_no or "",
        purchase_order_date=salesorder.purchase_order_date,
        delivery_date=salesorder.delivery_date,
        order_type=salesorder.order_type,
        project_name=salesorder.project_name,
        nalco_type=salesorder.nalco_type,
        tolerance=salesorder.tolerance,
        remarks=salesorder.remarks,
        terms_and_condition=salesorder.terms_and_condition,
        po_copy=salesorder.purchase_order_copy,
        approved_by=salesorder.approved_by,
        created_by=user,
        updated_by=user,
    )

    if salesorder.packing_mode.exists():
        workorder.packing_mode.set(salesorder.packing_mode.all())

    for so_detail in salesorder.inquiry_salesorder_details.filter(deleted=False):
        net_weight = so_detail.net_weight or Decimal(0)
        pieces = so_detail.pieces or 0

        wo_detail = WorkOrderDetail.objects.create(
            workorder=workorder,
            salesorder_detail=so_detail,
            die_profile=so_detail.section_no,
            alloy=so_detail.alloy,
            temper=so_detail.temper,
            length=so_detail.length,
            pieces=pieces,
            net_weight=net_weight,
            max_weight=so_detail.max_weight,
            min_weight=so_detail.min_weight,
            nalco_rate=so_detail.nalco_rate,
            modify_nalco_rate=so_detail.modify_nalco_rate,
            nalco_rate_change_reason=so_detail.nalco_rate_change_reason,
            conversion=so_detail.conversion,
            packing_cost=so_detail.packing_cost,
            customer_reference_number=so_detail.customer_reference_number,
            out_source=so_detail.out_source,
            cutting=so_detail.cutting,
            machining=so_detail.machining,
            deburring=so_detail.deburring,
            cutting_price=so_detail.cutting_price,
            machining_price=so_detail.machining_price,
            deburring_price=so_detail.deburring_price,
            anodising=so_detail.anodising,
            powder_coating=so_detail.powder_coating,
            pvdf=so_detail.pvdf,
            anodising_price=so_detail.anodising_price,
            anodising_description=so_detail.anodising_description,
            powder_coating_price=so_detail.powder_coating_price,
            powder_coating_description=so_detail.powder_coating_description,
            pvdf_price=so_detail.pvdf_price,
            pvdf_description=so_detail.pvdf_description,
            laser_marking_price=so_detail.laser_marking_price,
            laser_marking_description=so_detail.laser_marking_description,
            pending_weight=net_weight,
            pending_pieces=pieces,
            created_by=user,
            updated_by=user,
        )

        if so_detail.surface_finish.exists():
            wo_detail.surface_finish.set(so_detail.surface_finish.all())

    # Init process tracking (item-wise checklist) — does not change legacy status
    from workorder.process_tracking import bootstrap_tracks_for_workorder

    bootstrap_tracks_for_workorder(workorder, user=user)

    salesorder.status = "WorkOrder"
    salesorder.workorder_converted_date = timezone.now().date()
    salesorder.save(update_fields=["status", "workorder_converted_date"])

    return workorder

def _delete_workorder_from_salesorder(salesorder, user):
    workorder = WorkOrder.objects.filter(salesorder=salesorder, deleted=False).first()
    if not workorder:
        return None, None 
    in_process_details = WorkOrderDetail.objects.filter(workorder=workorder, deleted=False, status="In Process").exists()
    if in_process_details:
        return None, "This sales order cannot be deleted because one or more linked work order details are currently In Process."

    WorkOrderDetail.objects.filter(workorder=workorder, deleted=False
    ).update(deleted=True, deleted_by=user, deleted_at=timezone.now())

    workorder.deleted = True
    workorder.deleted_by = user
    workorder.deleted_at = timezone.now()
    workorder.save()

    return workorder, None

def _delete_workorder_detail_from_salesorder_detail(salesorder_detail, user):
    wo_detail = WorkOrderDetail.objects.filter(
        salesorder_detail=salesorder_detail, deleted=False
    ).first()

    if not wo_detail:
        return None, None

    if wo_detail.status == "In Process":
        return None, "This sales order detail cannot be deleted because the linked work order detail is currently In Process."

    wo_detail.deleted = True
    wo_detail.deleted_by = user
    wo_detail.deleted_at = timezone.now()
    wo_detail.save()

    return wo_detail, None

class InquirySalesOrderViewSet(BaseModelViewSet):
    queryset = InquirySalesOrder.objects.select_related(
        "created_by", "updated_by", "bill_to", "ship_to", "inquiry"
    ).prefetch_related("packing_mode").exclude(status="Pending_Fixed_Rate_Approval").order_by("sales_order_no")
    serializer_class = InquirySalesOrderSerializer
    list_serializer_class = InquirySalesOrderListSerializer
    fy_filtering_enabled = False

    def get_queryset(self):
        user = self.request.user

        queryset = (
            InquirySalesOrder.objects.select_related(
                "created_by",
                "updated_by",
                "bill_to",
                "ship_to",
                "inquiry",
            )
            .prefetch_related("packing_mode")
            .filter(deleted=False)
            .exclude(status="Pending_Fixed_Rate_Approval")
            .order_by("-created_at")
        )

        if user.is_superuser or user.groups.filter(name__in=["Super Admin", "Admin"]).exists():

            sales_executive = self.request.query_params.get("sales_executive")

            if sales_executive:
                queryset = queryset.filter(
                    bill_to__sales_executive_id=sales_executive
                )

            return queryset
        is_sales_person = Customer.objects.filter(sales_executive_id=user.id).exists()

        if is_sales_person:
            return queryset.filter(
                bill_to__sales_executive_id=user.id
            )

        if user.has_perm("inquiry_salesorder.view_inquirysalesorder"):
            return queryset
    
        return queryset.none()
    
    search_fields = [
        "sales_order_no", 
        "purchase_order_no",
        "remarks",
        "status",
        "bill_to__customer_name",
        "created_by__first_name",
    ]
    ordering_fields = [
        "sales_order_no",
        "purchase_order_no",
        "purchase_order_date",
        "order_date",
        "delivery_date",
        "created_at",
        "updated_at",
        "workorder_converted_date",
        "status",
        "inquiry__inquiry_number",
        "inquiry__customer_name",
    ]

    def create(self, request, *args, **kwargs):
        try:
            if "data" in request.data:
                data_str = request.data.get("data")

                if isinstance(data_str, str):
                    try:
                        parsed_data = json.loads(data_str)
                    except json.JSONDecodeError as e:
                        return Response(
                            {
                                "success": False,
                                "message": f"Invalid JSON format in 'data' field: {str(e)}",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    parsed_data = data_str

                salesorder_details_data = parsed_data.pop(
                    "inquiry_salesorder_details", []
                )
                packing_mode_ids = parsed_data.pop("packing_mode", [])
                serializer_data = parsed_data
            else:
                salesorder_details_data = request.data.get(
                    "inquiry_salesorder_details", []
                )
                packing_mode_ids = request.data.get("packing_mode", [])

                if isinstance(salesorder_details_data, str):
                    try:
                        salesorder_details_data = json.loads(salesorder_details_data)
                    except json.JSONDecodeError:
                        salesorder_details_data = []

                serializer_data = {
                    key: value
                    for key, value in request.data.items()
                    if key
                    not in [
                        "inquiry_salesorder_details",
                        "purchase_order_copy",
                        "packing_mode",
                        "data",
                    ]
                }

            purchase_order_copy = request.FILES.get("purchase_order_copy", None)
            serializer = InquirySalesOrderCreateSerializer(
                data=serializer_data, context={"request": request}
            )

            if serializer.is_valid():
                with transaction.atomic():
                    sales_order_no = generate_sales_order_number()
                    inquiry_salesorder = serializer.save(
                        sales_order_no=sales_order_no,
                        created_by=request.user,
                        updated_by=request.user,
                    )

                    if packing_mode_ids is not None:
                        inquiry_salesorder.packing_mode.set(packing_mode_ids)

                    if purchase_order_copy:
                        inquiry_salesorder.upload_doc(
                            {"purchase_order_copy": purchase_order_copy}
                        )

                    for detail_data in salesorder_details_data:
                        surface_finish_ids = detail_data.pop("surface_finish", [])

                        detail_serializer = InquirySalesOrderDetailCreateSerializer(
                            data=detail_data
                        )
                        if detail_serializer.is_valid():
                            salesorder_detail = detail_serializer.save(
                                inquiry_salesorder=inquiry_salesorder,
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            if surface_finish_ids:
                                salesorder_detail.surface_finish.set(surface_finish_ids)
                        else:
                            return Response(
                                {
                                    "success": False,
                                    "message": "Invalid sales order detail data.",
                                    "errors": detail_serializer.errors,
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    try:
                        payload = clean_payload(serializer_data)
                        log_user_activity(
                            user=request.user,
                            action="CREATE",
                            module_name="InquirySalesOrder",
                            description=f"Created InquirySalesOrder {inquiry_salesorder.sales_order_no}",
                            request=request,
                            payload=payload,
                        )
                    except Exception:
                        pass


                    if inquiry_salesorder.nalco_type == "Variable":
                        _create_workorder_from_salesorder(inquiry_salesorder, request.user)

                    inquiry_salesorder.refresh_from_db()
                    response_serializer = InquirySalesOrderSerializer(
                        inquiry_salesorder
                    )

                    return Response(
                        {
                            "success": True,
                            "message": "Inquiry sales order created successfully.",
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
                    "message": f"Error creating inquiry sales order: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data_str = request.data.get("data")

            if data_str:
                try:
                    json_data = json.loads(data_str)
                except json.JSONDecodeError:
                    return Response(
                        {"success": False, "message": "Invalid JSON in 'data' field."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                salesorder_details_data = json_data.pop(
                    "inquiry_salesorder_details", []
                )
                po_file = request.FILES.get("purchase_order_copy")

                serializer = self.get_serializer(instance, data=json_data, partial=True)
                if not serializer.is_valid():
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid sales order data.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                with transaction.atomic():
                    salesorder = serializer.save(updated_by=request.user)
                    existing_detail_ids = set(salesorder.inquiry_salesorder_details.filter(deleted=False).values_list("id", flat=True)
)
                    if po_file:
                        salesorder.upload_doc({"purchase_order_copy": po_file})

                    created_details = []
                    for idx, detail_data in enumerate(salesorder_details_data):
                        if detail_data.get("id"):
                            try:
                                detail_obj = InquirySalesOrderDetail.objects.get(
                                    id=detail_data["id"]
                                )
                            except InquirySalesOrderDetail.DoesNotExist:
                                return Response(
                                    {
                                        "success": False,
                                        "message": f"Detail with id {detail_data['id']} not found.",
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                            wo_detail = WorkOrderDetail.objects.filter(
                                salesorder_detail=detail_obj, deleted=False
                            ).first()
                            if wo_detail and wo_detail.status != "Pending":
                                detail_name = (
                                    f"{detail_obj.section_no.die_number} - "
                                    f"{detail_obj.alloy.alloy_code} - "
                                    f"{detail_obj.temper.temper_code_new}"
                                )
                                return Response(
                                    {
                                        "success": False,
                                        "message": f"Sales order detail {detail_name} cannot be updated because the linked work order detail is in '{wo_detail.status}' status.",
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                            detail_serializer = InquirySalesOrderDetailCreateSerializer(
                                detail_obj, data=detail_data, partial=True
                            )
                        else:
                            detail_serializer = InquirySalesOrderDetailCreateSerializer(
                                data=detail_data
                            )

                        if not detail_serializer.is_valid():
                            return Response(
                                {
                                    "success": False,
                                    "message": f"Invalid detail data at index {idx}.",
                                    "errors": detail_serializer.errors,
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        detail = detail_serializer.save(
                            inquiry_salesorder=salesorder,
                            created_by=(
                                request.user if not detail_data.get("id") else None
                            ),
                            updated_by=request.user,
                        )

                        surface_items = detail_data.get("surface_finish", [])
                        detail.surface_finish.set(
                            surface_items if surface_items else []
                        )

                        if surface_items:
                            job_names = set(
                                JobWorkType.objects.filter(
                                    id__in=surface_items
                                ).values_list("name", flat=True)
                            )
                            names_lower = {n.lower() for n in job_names}

                            if "cutting" not in detail_data:
                                detail.cutting = any(
                                    "cutting" in n for n in names_lower
                                )
                            if "machining" not in detail_data:
                                detail.machining = any(
                                    "machining" in n for n in names_lower
                                )
                            if "deburring" not in detail_data:
                                detail.deburring = any(
                                    "deburring" in n for n in names_lower
                                )
                            if "out_source" not in detail_data:
                                detail.out_source = any(
                                    "out source" in n or "outsource" in n
                                    for n in names_lower
                                )
                            if "anodising" not in detail_data:
                                detail.anodising = any(
                                    "anodising" in n or "anodizing" in n
                                    for n in names_lower
                                )
                            if "powder_coating" not in detail_data:
                                detail.powder_coating = any(
                                    "powder coating" in n
                                    or "powder_coating" in n
                                    or "powdercoating" in n
                                    for n in names_lower
                                )
                            if "pvdf" not in detail_data:
                                detail.pvdf = any("pvdf" in n for n in names_lower)
                        else:
                            for flag in (
                                "cutting",
                                "machining",
                                "deburring",
                                "out_source",
                                "anodising",
                                "powder_coating",
                                "pvdf",
                            ):
                                if flag not in detail_data:
                                    setattr(detail, flag, False)

                        for flag in (
                            "cutting",
                            "machining",
                            "deburring",
                            "out_source",
                            "anodising",
                            "powder_coating",
                            "pvdf",
                        ):
                            if flag in detail_data:
                                setattr(detail, flag, bool(detail_data[flag]))

                        detail.save()
                        if not detail_data.get("id"):
                            created_details.append(detail)

                    incoming_detail_ids = {d["id"] for d in salesorder_details_data if d.get("id")}
                    delete_detail_ids = existing_detail_ids - incoming_detail_ids
                    for so_detail in salesorder.inquiry_salesorder_details.filter(id__in=delete_detail_ids, deleted=False):
                        if so_detail.id not in incoming_detail_ids:
                            _, error = _delete_workorder_detail_from_salesorder_detail(so_detail, request.user)
                            if error:
                                return Response(
                                    {"success": False, "message": error},
                                    status=status.HTTP_400_BAD_REQUEST,
                                )
                            so_detail.deleted = True
                            so_detail.deleted_by = request.user
                            so_detail.deleted_at = timezone.now()
                            so_detail.save()

                    _update_workorder_from_salesorder(salesorder, request.user)

                    salesorder.refresh_from_db()
                    resp_serializer = self.get_serializer(salesorder)

                    log_user_activity(
                        user=request.user,
                        action="UPDATE",
                        module_name="InquirySalesOrder",
                        description=f"Updated SalesOrder + {len(created_details)} new details",
                        request=request,
                        payload=json_data,
                    )

                    return Response(
                        {
                            "success": True,
                            "message": "Sales order updated successfully.",
                            "data": resp_serializer.data,
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )
            else:
                po_file = request.FILES.get("purchase_order_copy")
                data = request.data.copy()

                remove_file = (
                    data.get("purchase_order_copy") in ["", "null", None]
                    and "purchase_order_copy" in data
                )

                if "purchase_order_copy" in data and po_file:
                    data.pop("purchase_order_copy")
                elif "purchase_order_copy" in data:
                    data.pop("purchase_order_copy")

                serializer = self.get_serializer(instance, data=data, partial=True)
                if not serializer.is_valid():
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid data.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                with transaction.atomic():
                    salesorder = serializer.save(updated_by=request.user)

                    if po_file:
                        salesorder.upload_doc({"purchase_order_copy": po_file})
                    elif remove_file:
                        if salesorder.purchase_order_copy:
                            delete_uploaded_file(salesorder.purchase_order_copy)
                        salesorder.purchase_order_copy = None
                        salesorder.save()

                    _update_workorder_from_salesorder(salesorder, request.user)

                    salesorder.refresh_from_db()
                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="UPDATE",
                        module_name="InquirySalesOrder",
                        description="Updated SalesOrder (no details)",
                        request=request,
                        payload=payload,
                    )
                    resp_serializer = self.get_serializer(salesorder)

                return Response(
                    {
                        "success": True,
                        "message": "Sales order updated successfully.",
                        "data": resp_serializer.data,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            _, error = _delete_workorder_from_salesorder(instance, request.user)
            if error:
                return Response(
                    {"success": False, "message": error},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.deleted = True
            instance.deleted_by = request.user
            instance.save()
            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name="InquirySalesOrder",
                description=f"Archived InquirySalesOrder",
                request=request,
                payload=payload,
            )
            return Response(
                {
                    "success": True,
                    "message": "Inquiry sales order deleted successfully.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
        
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting inquiry sales order detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="convert-to-workorder")
    def convert_to_workorder(self, request, pk=None):
        try:
            try:
                inquiry_salesorder = InquirySalesOrder.objects.select_related(
                    "inquiry", "bill_to", "ship_to"
                ).get(id=pk, deleted=False)
            except InquirySalesOrder.DoesNotExist:
                return Response(
                    {"success": False, "message": "Inquiry sales order not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            data_str = request.data.get("data")
            if data_str:
                if isinstance(data_str, str):
                    try:
                        parsed_data = json.loads(data_str)
                    except json.JSONDecodeError as e:
                        return Response(
                            {
                                "success": False,
                                "message": f"Invalid JSON format in 'data' field: {str(e)}",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    parsed_data = data_str
                workorder_details_data = parsed_data.get("work_order_details", [])
                if isinstance(workorder_details_data, str):
                    try:
                        workorder_details_data = json.loads(workorder_details_data)
                    except json.JSONDecodeError:
                        workorder_details_data = []
                packing_mode_ids = parsed_data.get("packing_mode", [])
                payload_data = parsed_data
            else:
                workorder_details_data = request.data.get("workorder_details", [])
                if isinstance(workorder_details_data, str):
                    try:
                        workorder_details_data = json.loads(workorder_details_data)
                    except json.JSONDecodeError:
                        workorder_details_data = []
                packing_mode_ids = request.data.get("packing_mode", [])
                payload_data = request.data

            if not workorder_details_data:
                return Response(
                    {"success": False, "message": "workorder_details is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                workorder = WorkOrder.objects.create(
                    order_no=derive_workorder_no_from_salesorder(inquiry_salesorder.sales_order_no),
                    order_date=timezone.now().date(),
                    salesorder=inquiry_salesorder,
                    bill_to_id=payload_data.get("bill_to"),
                    ship_to_id=payload_data.get("ship_to"),
                    purchase_order_no=payload_data.get("purchase_order_no")
                    or inquiry_salesorder.purchase_order_no
                    or "",
                    order_type=payload_data.get("order_type", "order"),
                    project_name=payload_data.get("project_name"),
                    approved_by_id=payload_data.get("approved_by"),
                    purchase_order_date=payload_data.get("purchase_order_date")
                    or inquiry_salesorder.purchase_order_date,
                    delivery_date=payload_data.get("delivery_date"),
                    nalco_type=payload_data.get("nalco_type", "Variable"),
                    tolerance=payload_data.get("tolerance", "Zero(0)"),
                    workorder_type=payload_data.get("workorder_type", "In_House"),
                    remarks=payload_data.get("remarks") or inquiry_salesorder.remarks,
                    created_by=request.user,
                    updated_by=request.user,
                )

                if packing_mode_ids:
                    workorder.packing_mode.set(packing_mode_ids)

                po_copy = request.FILES.get("po_copy")
                if po_copy:
                    workorder.upload_doc({"po_copy": po_copy})
                else:
                    purchase_order_copy = inquiry_salesorder.purchase_order_copy
                    if purchase_order_copy:
                        workorder.po_copy = purchase_order_copy
                        workorder.save(update_fields=["po_copy"])

                for detail_data in workorder_details_data:
                    net_weight = Decimal(detail_data.get("net_weight") or 0)
                    pieces = int(detail_data.get("pieces") or 0)
                    surface_finish_ids = detail_data.get("surface_finish", [])

                    wo_detail = WorkOrderDetail.objects.create(
                        workorder=workorder,
                        die_profile_id=detail_data.get("die_profile"),
                        alloy_id=detail_data.get("alloy"),
                        temper_id=detail_data.get("temper"),
                        length=detail_data.get("length"),
                        pieces=pieces,
                        net_weight=net_weight,
                        max_weight=detail_data.get("max_weight"),
                        min_weight=detail_data.get("min_weight"),
                        nalco_rate=detail_data.get("nalco_rate"),
                        conversion=detail_data.get("conversion"),
                        packing_cost=detail_data.get("packing_cost"),
                        customer_reference_number=detail_data.get("customer_reference_number"),
                        description=detail_data.get("description"),
                        out_source=detail_data.get("out_source", False),
                        cutting=detail_data.get("cutting", False),
                        machining=detail_data.get("machining", False),
                        deburring=detail_data.get("deburring", False),
                        cutting_price=detail_data.get("cutting_price"),
                        machining_price=detail_data.get("machining_price"),
                        deburring_price=detail_data.get("deburring_price"),
                        anodising=detail_data.get("anodising", False),
                        powder_coating=detail_data.get("powder_coating", False),
                        pvdf=detail_data.get("pvdf", False),
                        anodising_price=detail_data.get("anodising_price"),
                        anodising_description=detail_data.get("anodising_description"),
                        powder_coating_price=detail_data.get("powder_coating_price"),
                        powder_coating_description=detail_data.get(
                            "powder_coating_description"
                        ),
                        pvdf_price=detail_data.get("pvdf_price"),
                        pvdf_description=detail_data.get("pvdf_description"),
                        laser_marking_price=detail_data.get("laser_marking_price"),
                        laser_marking_description=detail_data.get(
                            "laser_marking_description"
                        ),
                        pending_weight=net_weight,
                        pending_pieces=pieces,
                        created_by=request.user,
                        updated_by=request.user,
                    )

                    if surface_finish_ids:
                        wo_detail.surface_finish.set(
                            JobWorkType.objects.filter(id__in=surface_finish_ids)
                        )

                inquiry_salesorder.status = "WorkOrder"
                inquiry_salesorder.workorder_converted_date = timezone.now().date()
                inquiry_salesorder.updated_by = request.user
                inquiry_salesorder.save()

                try:
                    log_user_activity(
                        user=request.user,
                        action="CONVERT",
                        module_name="InquirySalesOrder",
                        description=f"Converted sales order {inquiry_salesorder.sales_order_no} to work order {workorder.order_no}",
                        request=request,
                        payload=clean_payload(request.data),
                    )
                except Exception:
                    pass

                return Response(
                    {
                        "success": True,
                        "message": "Sales order converted to work order successfully",
                        "data": {
                            "id": workorder.id,
                            "order_no": workorder.order_no,
                            "order_date": workorder.order_date,
                            "bill_to": workorder.bill_to_id,
                            "ship_to": workorder.ship_to_id,
                            "salesorder": workorder.salesorder_id,
                            "purchase_order_no": workorder.purchase_order_no,
                            "purchase_order_date": workorder.purchase_order_date,
                            "delivery_date": workorder.delivery_date,
                            "nalco_type": workorder.nalco_type,
                            "tolerance": workorder.tolerance,
                            "workorder_type": workorder.workorder_type,
                            "remarks": workorder.remarks,
                            "packing_mode": list(
                                workorder.packing_mode.values_list("id", flat=True)
                            ),
                            "sales_order_no": inquiry_salesorder.sales_order_no,
                            "workorder_converted_date": inquiry_salesorder.workorder_converted_date,
                            "created_at": workorder.created_at,
                            "updated_at": workorder.updated_at,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error converting to work order: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InquirySalesOrderArchiveViewSet(viewsets.ModelViewSet):
    queryset = InquirySalesOrder.objects.filter(deleted=True).order_by("-id")
    serializer_class = InquirySalesOrderArchiveListSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    search_fields = [
        "purchase_order_no",
        "packing_mode",
        "inquiry__inquiry_number",
        "inquiry__customer_name",
    ]
    ordering_fields = [
        "purchase_order_no",
        "purchase_order_date",
        "order_date",
        "created_at",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")

        if no_pagination:
            serializer = InquirySalesOrderArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        if page is not None:
            serializer = InquirySalesOrderArchiveListSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = InquirySalesOrderArchiveListSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})


class InquiryFixedSalesOrderViewSet(BaseModelViewSet):
    queryset = InquirySalesOrder.objects.filter(status="Pending_Fixed_Rate_Approval").select_related(
        "created_by", "updated_by", "bill_to", "ship_to", "inquiry"
    ).prefetch_related("packing_mode")
    serializer_class = InquirySalesOrderSerializer
    list_serializer_class = InquirySalesOrderListSerializer  

    @action(detail=True, methods=["patch"], url_path="approve")
    def approve_salesorder(self, request, pk=None):
        try:
            inquiry_salesorder = self.get_object()
            approval_reason = request.data.get("approval_reason")
            approved_by = request.user

            if not approved_by or not approval_reason.strip():
                return Response(
                    {
                        "success": False,
                        "message": "Approval Reason is Compulsory.",
                        "errors": {"Approval Reason": ["This field is required."]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                inquiry_salesorder.approval_reason = approval_reason.strip()
                inquiry_salesorder.approved_by = approved_by
                inquiry_salesorder.approved_at = timezone.now() 
                inquiry_salesorder.status = "WorkOrder"
                inquiry_salesorder.updated_by = request.user
                inquiry_salesorder.updated_at = timezone.now()
                inquiry_salesorder.save()

                _create_workorder_from_salesorder(inquiry_salesorder, request.user)

            except ValidationError as e:
                return Response(
                    {
                        "success": False,
                        "message": "File upload failed.",
                        "errors": (
                            e.message_dict
                            if hasattr(e, "message_dict")
                            else {"upload_errors": e.messages}
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                return Response(
                    {"success": False, "message": f"File processing error: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            try:
                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="InquirySalesOrder",
                    description=f"Inquiry Salesorder {inquiry_salesorder.sales_order_no} Approved Successfully.",
                    request=request,
                    payload={
                        "approved_reason": approval_reason,
                    },
                )
            except:
                pass

            serializer = InquirySalesOrderListSerializer(inquiry_salesorder)
            return Response(
                {
                    "success": True,
                    "message": "Inquiry Salesorder Approved Successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except InquirySalesOrder.DoesNotExist:
            return Response(
                {"success": False, "message": "Inquiry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InquirySalesOrderDetailViewSet(BaseModelViewSet):
    queryset = InquirySalesOrderDetail.objects.all()
    serializer_class = InquirySalesOrderDetailSerializer

    search_fields = [
        "inquiry_salesorder__sales_order_no",
        "inquiry_salesorder__purchase_order_no",
        "inquiry_salesorder__inquiry__inquiry_number",
        "inquiry_salesorder__inquiry__customer_name",
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
        "created_at",
        "updated_at",
        "length",
        "pieces",
        "inquiry_salesorder__sales_order_no",
        "alloy__name",
        "temper__name",
    ]

    def get_queryset(self):
        return (
            InquirySalesOrderDetail.objects.filter(deleted=False)
            .select_related(
                "inquiry_salesorder",
                "alloy",
                "temper",
                "created_by",
                "updated_by",
                "deleted_by",
            )
            .prefetch_related("surface_finish")
            .order_by("-id")
        )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = request.data.copy()

            wo_detail = WorkOrderDetail.objects.filter(
                salesorder_detail=instance, deleted=False
            ).first()
            if wo_detail and wo_detail.status != "Pending":
                return Response(
                    {
                        "success": False,
                        "message": f"This sales order detail cannot be updated because the linked work order detail is in '{wo_detail.status}' status.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = self.get_serializer(instance, data=data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {
                        "success": False,
                        "message": "Invalid data.",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                detail = serializer.save(updated_by=request.user)

                surface_items = data.get("surface_finish", [])
                detail.surface_finish.set(surface_items if surface_items else [])

                if surface_items:
                    job_names = set(
                        JobWorkType.objects.filter(id__in=surface_items).values_list(
                            "name", flat=True
                        )
                    )
                    names_lower = {n.lower() for n in job_names}

                    for flag, keywords in [
                        ("cutting", ["cutting"]),
                        ("machining", ["machining"]),
                        ("deburring", ["deburring"]),
                        ("out_source", ["out source", "outsource"]),
                        ("anodising", ["anodising", "anodizing"]),
                        (
                            "powder_coating",
                            ["powder coating", "powder_coating", "powdercoating"],
                        ),
                        ("pvdf", ["pvdf"]),
                    ]:
                        if flag not in data:
                            setattr(
                                detail,
                                flag,
                                any(k in n for n in names_lower for k in keywords),
                            )
                else:
                    for flag in (
                        "cutting",
                        "machining",
                        "deburring",
                        "out_source",
                        "anodising",
                        "powder_coating",
                        "pvdf",
                    ):
                        if flag not in data:
                            setattr(detail, flag, False)

                for flag in (
                    "cutting",
                    "machining",
                    "deburring",
                    "out_source",
                    "anodising",
                    "powder_coating",
                    "pvdf",
                ):
                    if flag in data:
                        setattr(detail, flag, bool(data[flag]))

                detail.save()
                detail.refresh_from_db()

                _update_workorder_from_salesorder(detail.inquiry_salesorder, request.user)

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="InquirySalesOrderDetail",
                    description="Updated SalesOrder Detail",
                    request=request,
                    payload=payload,
                )
                resp_serializer = self.get_serializer(detail)

            return Response(
                {
                    "success": True,
                    "message": "Sales order detail updated successfully.",
                    "data": resp_serializer.data,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            surface_finish_ids = request.data.pop("surface_finish", [])
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    salesorder_detail = serializer.save(
                        created_by=request.user, updated_by=request.user
                    )

                    if surface_finish_ids:
                        salesorder_detail.surface_finish.set(surface_finish_ids)

                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="CREATE",
                        module_name="InquirySalesOrderDetail",
                        description=f"Created InquirySalesOrderDetail",
                        request=request,
                        payload=payload,
                    )
                    response_serializer = self.get_serializer(salesorder_detail)

                return Response(
                    {
                        "success": True,
                        "message": "Inquiry sales order detail created successfully.",
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
                    "message": f"Error creating inquiry sales order detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            surface_finish_ids = request.data.pop("surface_finish", None)

            wo_detail = WorkOrderDetail.objects.filter(
                salesorder_detail=instance, deleted=False
            ).first()
            if wo_detail and wo_detail.status != "Pending":
                return Response(
                    {
                        "success": False,
                        "message": f"This sales order detail cannot be updated because the linked work order detail is in '{wo_detail.status}' status.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    salesorder_detail = serializer.save(updated_by=request.user)

                    if surface_finish_ids is not None:
                        salesorder_detail.surface_finish.set(surface_finish_ids)

                    salesorder_detail.refresh_from_db()

                    _update_workorder_from_salesorder(salesorder_detail.inquiry_salesorder, request.user)

                    payload = clean_payload(request.data)
                    log_user_activity(
                        user=request.user,
                        action="UPDATE",
                        module_name="InquirySalesOrderDetail",
                        description=f"Updated InquirySalesOrderDetail",
                        request=request,
                        payload=payload,
                    )

                    response_serializer = self.get_serializer(salesorder_detail)

                return Response(
                    {
                        "success": True,
                        "message": "Inquiry sales order detail updated successfully.",
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
                    "message": f"Error updating inquiry sales order detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            _, error = _delete_workorder_detail_from_salesorder_detail(instance, request.user)
            if error:
                return Response(
                    {"success": False, "message": error},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.deleted = True
            instance.deleted_by = request.user
            instance.save()
            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name="InquirySalesOrderDetail",
                description=f"Archived InquirySalesOrderDetail",
                request=request,
                payload=payload,
            )
            return Response(
                {
                    "success": True,
                    "message": "Inquiry sales order detail deleted successfully.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting inquiry sales order detail: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
