import json
import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from product.models import Alloy, Temper
from django.db import models, transaction
from django.db.models import Prefetch, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from bundle_inward.models import BundleInward, ExcessStock
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from customer.models import Customer
from die.models import Die
from quotation.models import Quotation
from utils.error_handling import custom_exception
from utils.generate_number import generate_order_no
from utils.log_activity import clean_payload, log_user_activity
from workorder.models import WorkOrder, WorkOrderDetail
from workorder.serializers import WorkOrderDetailSerializers, WorkOrderSerializers
from workorder.sort_serializers import WorkOrderListSerializer

logger = logging.getLogger("file")


class WorkOrderViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializers
    list_serializer_class = WorkOrderListSerializer
    fy_filtering_enabled = False

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == "list":
            queryset = (
                queryset.select_related(
                    "bill_to", "ship_to", "salesorder", "approved_by" ,"created_by", "updated_by", "deleted_by"
                    ).prefetch_related("packing_mode").order_by("-order_no")
                .annotate(
                    total_weight_calc=Sum(
                        "workorder_detail_workorder__net_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_packed_weight_calc=Sum(
                        "workorder_detail_workorder__packed_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_dispatched_weight_calc=Sum(
                        "workorder_detail_workorder__dispatched_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_pending_weight_calc=Sum(
                        "workorder_detail_workorder__pending_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                )
            )
        elif self.action == "retrieve":
            queryset = (
                queryset.select_related(
                    "bill_to", "ship_to", "salesorder", "approved_by", "created_by", "updated_by", "deleted_by"
                )
                .prefetch_related(
                    Prefetch(
                        "workorder_detail_workorder",
                        queryset=WorkOrderDetail.objects.filter(deleted=False)
                        .select_related("die_profile", "alloy", "temper")
                        .prefetch_related("surface_finish"),
                    )
                )
                .annotate(
                    total_pieces_calc=Sum(
                        "workorder_detail_workorder__pieces",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    cut_length_calc=Sum(
                        "workorder_detail_workorder__length",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_weight_calc=Sum(
                        "workorder_detail_workorder__net_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_packed_weight_calc=Sum(
                        "workorder_detail_workorder__packed_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_dispatched_weight_calc=Sum(
                        "workorder_detail_workorder__dispatched_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                    total_pending_weight_calc=Sum(
                        "workorder_detail_workorder__pending_weight",
                        filter=Q(workorder_detail_workorder__deleted=False),
                    ),
                )
            )
        else:
            queryset = queryset.select_related(
                "bill_to", "ship_to", "salesorder", "approved_by", "created_by", "updated_by", "deleted_by"
            )

        return queryset

    search_fields = [
        "id",
        "bill_to__customer_name",
        "purchase_order_no",
        "status",
        "order_no",
    ]

    ordering_fields = [
        "id",
        "bill_to__customer_name",
        "order_date",
        "delivery_date",
        "purchase_order_no",
        "status",
        "order_no",
        "created_at",
        "updated_at",
    ]

    @action(detail=False, methods=["get"], url_path="statistics")
    def workorder_summary(self, request):
        today = date.today()
        yellow = 0
        orange = 0
        red = 0
        green = 0

        queryset = self.get_queryset()
        for item in queryset:
            if not item.order_date:
                continue
            days_diff = (today - item.order_date).days
            if item.status == "Closed":
                green += 1
            else:
                if 8 < days_diff <= 12:
                    yellow += 1
                elif 12 < days_diff <= 15:
                    orange += 1
                elif days_diff >= 16:
                    red += 1

        return Response(
            {
                "status": True,
                "data": {
                    "yellow": yellow,
                    "orange": orange,
                    "red": red,
                    "green": green,
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="statistics-open-workorder")
    def open_workorder_summary(self, request):
        today = date.today()
        yellow = 0
        orange = 0
        red = 0

        queryset = self.get_queryset().filter(status="Open")

        for item in queryset:
            if not item.order_date:
                continue

            days_diff = (today - item.order_date).days

            if 8 < days_diff <= 12:
                yellow += 1
            elif 12 < days_diff <= 15:
                orange += 1
            elif days_diff >= 16:
                red += 1

        return Response(
            {
                "status": True,
                "data": {
                    "yellow": yellow,
                    "orange": orange,
                    "red": red,
                },
            }
        )

    @action(detail=False, methods=["GET"], url_path="workorder-for-excess-stock")
    def filtered_status_workorders(self, request, *args, **kwargs):

        try:
            allowed_statuses = ["W/o create", "Open", "Planning", "Waiting for Packing"]
            queryset = (
                self.queryset.filter(status__in=allowed_statuses)
                .prefetch_related("workorder_detail_workorder")
                .select_related("created_by", "updated_by")
            )

            alloy_list = request.query_params.getlist("alloy", [])
            length_list = request.query_params.getlist("length", [])
            temper_list = request.query_params.getlist("temper", [])
            profile_list = request.query_params.getlist("profile", [])

            detail_filters = {"deleted": False}

            if alloy_list:
                detail_filters["alloy__name__in"] = alloy_list
            if length_list:
                length_list = [int(l) if l.isdigit() else l for l in length_list]
                detail_filters["length__in"] = length_list
            if temper_list:
                detail_filters["temper__temper_code_new__in"] = temper_list
            if profile_list:
                detail_filters["die_profile__die_number__in"] = profile_list
            response_data = []

            for workorder in queryset:
                filtered_details = workorder.workorder_detail_workorder.filter(
                    **detail_filters
                )
                for detail in filtered_details:
                    response_data.append(
                        {
                            "id": workorder.id,
                            "workroder_detail_id": detail.id,
                            "workorder_no": workorder.order_no,
                            "length": detail.length,
                            "die_profile": (
                                detail.die_profile.die_number
                                if detail.die_profile
                                else None
                            ),
                            "packed_weight": f"{float(detail.packed_weight or 0):.3f}",
                            "dispatched_weight": f"{float(detail.dispatched_weight or 0):.3f}",
                            "net_weight": f"{float(detail.net_weight or 0):.3f}",
                            "alloy": detail.alloy.alloy_code if detail.alloy else None,
                            "temper": detail.temper.temper_code_new if detail.temper else None,
                        }
                    )

            page = self.paginate_queryset(response_data)
            if page is not None:
                return self.get_paginated_response({"success": True, "data": page})

            return Response(
                {"success": True, "data": response_data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            raw_data = request.data.get("data")
            if not raw_data:
                return Response(
                    {"success": False, "message": "Missing 'data' in form-data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return Response(
                    {"success": False, "message": "Invalid JSON format in 'data'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data["order_no"] = generate_order_no(self)
            data["created_by"] = request.user.id
            data["created_at"] = timezone.now()
            data["updated_at"] = None

            work_order_details_data = data.get("work_order_details", [])
            detail_errors = []
            main_errors = {}

            die_profile_ids = set()
            alloy_ids = set()
            temper_ids = set()

            for detail in work_order_details_data:
                if detail.get("die_profile"):
                    die_profile_ids.add(detail.get("die_profile"))
                if detail.get("alloy"):
                    alloy_ids.add(detail.get("alloy"))
                if detail.get("temper"):
                    temper_ids.add(detail.get("temper"))

            die_map = {
                obj.id: obj.die_number
                for obj in Die.objects.filter(id__in=die_profile_ids)
            }

            alloy_map = {
                obj.id: f"{obj.alloy_code} - {obj.standard}"
                for obj in Alloy.objects.filter(id__in=alloy_ids)
            }

            temper_map = {
                obj.id: obj.temper_code_new for obj in Temper.objects.filter(id__in=temper_ids)
            }

            seen_combinations = set()

            for index, detail in enumerate(work_order_details_data):
                die_profile_id = detail.get("die_profile")
                length = detail.get("length")
                alloy_id = detail.get("alloy")
                temper_id = detail.get("temper")

                if (
                    die_profile_id is not None
                    and length is not None
                    and alloy_id is not None
                    and temper_id is not None
                ):
                    combination = (die_profile_id, length, alloy_id, temper_id)

                    if combination in seen_combinations:
                        detail_errors.append(
                            {
                                "row": index,
                                "die_profile": f"Section with {die_map.get(die_profile_id, die_profile_id)} number already exists",
                                "length": length,
                                "alloy": f"Alloy with {alloy_map.get(alloy_id, alloy_id)} code already exists",
                                "temper": f"Temper with {temper_map.get(temper_id, temper_id)} name already exists",
                                "error": "Duplicate combination of Section, Length, Alloy and Temper.",
                            }
                        )
                    else:
                        seen_combinations.add(combination)

            file_obj = request.FILES.get("po_copy")
            serializer = self.serializer_class(data=data, context={"request": request})

            if not serializer.is_valid():
                main_errors.update(serializer.errors)

            if main_errors or detail_errors:
                response_data = {}

                if main_errors:
                    response_data.update(main_errors)

                if detail_errors:
                    response_data["work_order_details"] = detail_errors

                return Response(
                    {
                        "success": False,
                        "message": "Invalid workorder data",
                        "errors": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance = serializer.save()
            try:
                from workorder.process_tracking import bootstrap_tracks_for_workorder

                bootstrap_tracks_for_workorder(instance, user=request.user)
            except Exception:
                pass
            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Workorder",
                description=f"Created Workorder '{instance.order_no}'",
                request=request,
                payload=payload,
            )

            doc_dict = {"po_copy": file_obj}
            instance.upload_doc(doc_dict)

            logger.info("Record created successfully.")

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as ve:
            logger.error(f"Validation error: {str(ve)}")
            return Response(
                {"success": False, "message": str(ve)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"success": False, "message": "Something went wrong."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            try:
                raw_data = request.data.get("data", "{}")
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid JSON format in 'data' field.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data["updated_by"] = request.user.id
            data["updated_at"] = timezone.now()

            instance = self.get_object()

            main_errors = {}
            detail_errors = []

            if "po_copy" in request.FILES:
                try:
                    instance.upload_doc({"po_copy": request.FILES["po_copy"]})
                    data["po_copy"] = instance.po_copy
                except ValidationError as ve:
                    main_errors["po_copy"] = ve.detail
                except Exception as e:
                    main_errors["po_copy"] = [f"File upload failed: {str(e)}"]

            work_order_details_data = data.get("work_order_details", []) or []

            die_profile_ids = set()
            alloy_ids = set()
            temper_ids = set()

            for detail in work_order_details_data:
                if detail.get("die_profile"):
                    die_profile_ids.add(detail.get("die_profile"))
                if detail.get("alloy"):
                    alloy_ids.add(detail.get("alloy"))
                if detail.get("temper"):
                    temper_ids.add(detail.get("temper"))

            die_map = {
                obj.id: obj.die_number
                for obj in Die.objects.filter(id__in=die_profile_ids)
            }

            alloy_map = {
                obj.id: f"{obj.alloy_code} - {obj.standard}"
                for obj in Alloy.objects.filter(id__in=alloy_ids)
            }

            temper_map = {
                obj.id: obj.temper_code_new for obj in Temper.objects.filter(id__in=temper_ids)
            }

            seen_combinations = set()

            for index, detail in enumerate(work_order_details_data):
                die_profile_id = detail.get("die_profile")
                length = detail.get("length")
                alloy_id = detail.get("alloy")
                temper_id = detail.get("temper")

                if (
                    die_profile_id is not None
                    and length is not None
                    and alloy_id is not None
                    and temper_id is not None
                ):
                    combination = (die_profile_id, length, alloy_id, temper_id)

                    if combination in seen_combinations:
                        detail_errors.append(
                            {
                                "row": index,
                                "die_profile": f"Section with {die_map.get(die_profile_id, die_profile_id)} number already exists",
                                "length": length,
                                "alloy": f"Alloy with {alloy_map.get(alloy_id, alloy_id)} name already exists",
                                "temper": f"Temper with {temper_map.get(temper_id, temper_id)} name already exists",
                                "error": "Duplicate combination of die_profile, length, alloy and temper.",
                            }
                        )
                    else:
                        seen_combinations.add(combination)

            serializer = self.get_serializer(instance, data=data, partial=True)

            if not serializer.is_valid():
                main_errors.update(serializer.errors)

            if main_errors or detail_errors:
                response_data = {}

                if main_errors:
                    response_data.update(main_errors)

                if detail_errors:
                    response_data["work_order_details"] = detail_errors

                return Response(
                    {
                        "success": False,
                        "message": "Invalid workorder data",
                        "errors": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for detail_data in work_order_details_data:
                detail_id = detail_data.get("id")
                if not detail_id:
                    continue

                try:
                    detail_instance_log = WorkOrderDetail.objects.get(id=detail_id)
                except WorkOrderDetail.DoesNotExist:
                    continue

                old_value = detail_instance_log.die_over_weight
                new_value = detail_data.get("die_over_weight")

                if old_value != new_value:
                    die_number = (
                        detail_instance_log.die_profile.die_number
                        if detail_instance_log.die_profile
                        else "N/A"
                    )
                    length = detail_instance_log.length or "N/A"
                    order_no = instance.order_no

                    if new_value is True:
                        description = f"Die over weight applied to profile {die_number} of {length}mm length in work order {order_no}."
                    elif new_value is False:
                        description = f"Die over weight removed from profile {die_number} of {length}mm length in work order {order_no}."
                    else:
                        description = None

                    if description:
                        payload = clean_payload(request.data)
                        log_user_activity(
                            user=request.user,
                            action="UPDATE",
                            module_name="WorkorderDetail",
                            description=description,
                            request=request,
                            payload=payload,
                        )

            instance = serializer.save()

            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="Workorder",
                description=f"Updated Workorder '{instance.order_no}'",
                request=request,
                payload=payload,
            )

            skipped_updates = serializer.context.get("skipped_updates", [])

            response_data = {
                "success": True,
                "data": self.get_serializer(instance).data,
            }

            if skipped_updates:
                response_data["skipped_updates_count"] = len(skipped_updates)
                response_data["skipped_updates"] = skipped_updates
                response_data["message"] = (
                    f"Workorder updated successfully. {len(skipped_updates)} detail(s) were partially updated (only die_over_weight field) due to non-pending status."
                )

            return Response(response_data, status=status.HTTP_202_ACCEPTED)

        except ValidationError as ve:
            logger.error(f"Validation error: {str(ve)}")
            return Response(
                {"success": False, "message": str(ve)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            import traceback

            logger.error(traceback.format_exc())
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            instance.deleted = True
            instance.save(update_fields=["deleted"])

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="ARCHIVE",
                module_name="Workorder",
                description=f"Archived Workorder '{instance.order_no}'",
                request=request,
                payload=payload,
            )

            child_workorders = WorkOrder.objects.filter(
                reference_wo=instance, workorder_type="Job Work", deleted=False
            )

            for child in child_workorders:
                child.deleted = True
                child.save(update_fields=["deleted"])

                log_user_activity(
                    user=request.user,
                    action="ARCHIVE",
                    module_name="Workorder",
                    description=f"Archived Child Jobwork Workorder '{child.order_no}' (Parent: {instance.order_no})",
                    request=request,
                    payload=payload,
                )

            return Response(
                {
                    "success": True,
                    "message": "WorkOrder and related child surface_finish archived.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            return custom_exception(e)

    @action(detail=True, methods=["GET"], url_path="get-workorder-details-summery")
    def get_workorder_details_summery(self, request, pk=None, *args, **kwargs):
        try:
            work_order = self.get_object()
            detail_ids = request.query_params.getlist("detail_ids")
            work_order_details = WorkOrderDetail.objects.filter(
                id__in=detail_ids, workorder=work_order, deleted=False
            ).order_by("workorder_id", "die_profile_id", "id")

            summary_data = {
                "Order": {"pieces": 0, "net_weight": 0.00},
                "Packed": {"pieces": 0, "packed_weight": 0.00},
                "Dispatched": {"pieces": 0, "dispatched_weight": 0.00},
                "Pending": {"pieces": 0, "pending_weight": 0.00},
            }

            aggregate_data = work_order_details.aggregate(
                total_order_pieces=Sum("pieces"),
                total_order_weight=Sum("net_weight"),
                total_packed_pieces=Sum(
                    "pieces", filter=models.Q(workorder__status="Packed")
                ),
                total_packed_weight=Sum("packed_weight"),
                total_dispatched_pieces=Sum(
                    "pieces", filter=models.Q(workorder__status="Dispatched")
                ),
                total_dispatched_weight=Sum("dispatched_weight"),
                total_pending_pieces=Sum("pieces"),
                total_pending_weight=Sum("pending_weight"),
            )

            summary_data["Order"]["pieces"] = aggregate_data["total_order_pieces"] or 0
            summary_data["Order"]["net_weight"] = float(
                aggregate_data["total_order_weight"] or 0.0
            )

            summary_data["Packed"]["pieces"] = (
                aggregate_data["total_packed_pieces"] or 0
            )
            summary_data["Packed"]["packed_weight"] = float(
                aggregate_data["total_packed_weight"] or 0.0
            )

            summary_data["Dispatched"]["pieces"] = (
                aggregate_data["total_dispatched_pieces"] or 0
            )
            summary_data["Dispatched"]["dispatched_weight"] = float(
                aggregate_data["total_dispatched_weight"] or 0.0
            )

            summary_data["Pending"]["pieces"] = (
                aggregate_data["total_pending_pieces"] or 0
            )
            summary_data["Pending"]["pending_weight"] = float(
                aggregate_data["total_pending_weight"] or 0.00
            )

            return Response(
                {"success": True, "summary": summary_data}, status=status.HTTP_200_OK
            )

        except WorkOrder.DoesNotExist:
            return Response(
                {"detail": "Work order not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["PATCH"], url_path="close-workorder")
    def close_workorder(self, request, pk=None, *args, **kwargs):
        try:
            work_order = self.get_object()

            reason = request.data.get("reason_to_close")
            if not reason:
                raise ValidationError({"reason_to_close": "This field is required."})

            work_order.reason_to_close = reason
            work_order.status = "Closed"
            work_order.updated_by = request.user
            work_order.updated_at = timezone.now()

            doc_dict = {"wo_closing_doc": request.FILES.get("wo_closing_doc")}
            work_order.upload_doc(doc_dict)

            work_order.save()

            try:
                from workorder.process_tracking import advance_process

                for detail in work_order.workorder_detail_workorder.filter(deleted=False):
                    advance_process(
                        workorder_detail=detail,
                        stage="CLOSED",
                        user=request.user,
                        remarks="Work order closed",
                    )
            except Exception:
                pass

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="UPDATE",
                module_name="WorkOrder",
                description=f"Closed WorkOrder '{getattr(work_order, 'order_no')}",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "message": "Work order closed successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return custom_exception(e)

    @action(
        detail=False,
        methods=["GET"],
        url_path=r"(?P<die_id>\d+)/workorder-by-die-profile",
    )
    def workorder_by_die_profile(self, request, die_id=None):
        """
        API to get a list of work orders filtered by Die ID.
        """

        planning_status = request.query_params.get("planning_status")

        work_orders = WorkOrder.objects.filter(
            workorder_detail_workorder__die_profile_id=die_id
        ).distinct()

        if planning_status:
            work_orders = work_orders.filter(planning_status=planning_status)

        if not work_orders.exists():
            return Response(
                {"success": False, "message": "No work orders found for this Die ID."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(work_orders, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @transaction.atomic
    @action(
        detail=False,
        methods=["post"],
        url_path="convert-workorder",
        parser_classes=[MultiPartParser, FormParser],
    )
    def convert_to_workorder(self, request, *args, **kwargs):
        try:
            raw_data = request.data.get("data")
            if not raw_data:
                return Response(
                    {"success": False, "message": "Missing 'data' in form-data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return Response(
                    {"success": False, "message": "Invalid JSON format in 'data'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data["order_no"] = generate_order_no(self)
            data["created_by"] = request.user.id
            data["created_at"] = timezone.now()
            data["updated_at"] = None

            work_order_details_data = data.get("work_order_details", [])
            seen_combinations = set()

            for detail in work_order_details_data:
                die_profile_id = detail.get("die_profile")
                length = detail.get("length")

                if die_profile_id is not None and length is not None:
                    combination = (die_profile_id, length)
                    if combination in seen_combinations:
                        return Response(
                            {
                                "success": False,
                                "message": f"Duplicate entry found for die_profile ID {die_profile_id} and length {length} in the same work order.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    seen_combinations.add(combination)

            file_obj = request.FILES.get("po_copy")
            serializer = self.serializer_class(data=data, context={"request": request})
            if serializer.is_valid():
                work_order = serializer.save()

                doc_dict = {
                    "po_copy": file_obj,
                }
                work_order.upload_doc(doc_dict)

                quotation_no = data.get("quotation_no")
                try:
                    quotation = Quotation.objects.get(
                        quotation_no=quotation_no, deleted=False
                    )
                    quotation.status = "WorkOrder"
                    quotation.converted_date = timezone.now()
                    quotation.workorder_no = work_order.order_no
                    quotation.save()
                except Quotation.DoesNotExist:
                    logger.error(f"Quotation with number {quotation_no} not found.")
                    return Response(
                        {"success": False, "message": "Quotation not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="CONVERT",
                    module_name="Workorder",
                    description=f"Converted Workorder '{work_order.order_no}'",
                    request=request,
                    payload=payload,
                )

                logger.info("WorkOrder converted successfully.")
                response_data = self.serializer_class(
                    work_order, context={"request": request}
                ).data

                return Response(
                    {
                        "success": True,
                        "message": "Quotation successfully converted to WorkOrder",
                        "data": response_data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            else:
                logger.error(
                    f"Serializer errors during WorkOrder conversion: {serializer.errors}"
                )
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return Response(
                {"success": False, "message": f"Error creating workorder: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="get-excess-stock-summary")
    def get_excess_stock_summary(self, request):
        try:
            profile_id = int(request.query_params.get("profile_id"))
            length = request.query_params.get("length")
            alloy_id = int(request.query_params.get("alloy_id"))
            temper_id = int(request.query_params.get("temper_id"))

            die_number = Die.objects.get(id=profile_id).die_number

            qs = ExcessStock.objects.filter(
                die_profile_id=profile_id,
                length=length,
                alloy_id=alloy_id,
                temper_id=temper_id,
            )

            return Response(
                {
                    "success": True,
                    "message": "Excess stock summary fetched successfully",
                    "data": {
                        "profile_id": profile_id,
                        "die_number": die_number,
                        "length": length,
                        "alloy_id": alloy_id,
                        "temper_id": temper_id,
                        "total_bundles": qs.count(),
                        "total_weight": float(
                            qs.aggregate(Sum("weight"))["weight__sum"] or 0
                        ),
                        "total_pieces": qs.aggregate(Sum("pieces"))["pieces__sum"] or 0,
                    },
                }
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

    @action(detail=True, methods=["GET"], url_path="get-workorder-details")
    def get_workorder_details(self, request, pk=None, *args, **kwargs):
        try:
            work_order = self.get_object()
            work_order_details = WorkOrderDetail.objects.filter(
                workorder=work_order, deleted=False
            ).order_by("workorder_id", "die_profile_id", "id")

            serializer = WorkOrderDetailSerializers(work_order_details, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except WorkOrder.DoesNotExist:
            return Response(
                {"detail": "Work order not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["get"], url_path="report-by-workorder-filter")
    def report_by_workorder_filter(self, request):
        try:
            customer_id = request.query_params.get("customer_id")
            die_id = request.query_params.get("die_id")

            workorders = WorkOrder.objects.filter(
                deleted=False, status__in=["Open", "Warehouse", "Dispatched", "Packed"]
            ).select_related("bill_to")

            if customer_id:
                workorders = workorders.filter(bill_to_id=customer_id)

            if die_id:
                workorders = workorders.filter(
                    workorder_detail_workorder__die_profile_id=die_id
                ).distinct()

            full_data = []
            summary = {
                "order_pcs": 0,
                "order_kgs": 0,
                "dispatched_pcs": 0,
                "dispatched_kgs": 0,
                "packed_pcs": 0,
                "packed_kgs": 0,
                "warehouse_pcs": 0,
                "warehouse_kgs": 0,
                "pending_pcs": 0,
                "pending_kgs": 0,
            }

            for workorder in workorders:
                details = (
                    WorkOrderDetail.objects.filter(workorder=workorder, deleted=False)
                    .select_related("die_profile", "alloy", "temper")
                    .exclude(status="Pending")
                )

                if die_id:
                    details = details.filter(die_profile_id=die_id)

                total_kgs = details.aggregate(total=Sum("net_weight"))["total"] or 0
                if not details.exists():
                    row = {
                        "workorder_no": f"{workorder.order_no} / {workorder.order_date.strftime('%d-%m-%Y')}",
                        "po_no": f"{workorder.purchase_order_no}",
                        "workorder_detail_id": None,
                        "is_priority": False,
                        "section": None,
                        "profile_image": None,
                        "length": None,
                        "customer_reference_number": None,
                        "customer_name": (
                            workorder.bill_to.customer_name
                            if workorder.bill_to
                            else None
                        ),
                        "alloy_temper": None,
                        "order_pcs": 0,
                        "order_kgs": 0,
                        "dispatched_pcs": 0,
                        "dispatched_kgs": 0,
                        "packed_pcs": 0,
                        "packed_kgs": 0,
                        "warehouse_pcs": 0,
                        "warehouse_kgs": 0,
                        "pending_pcs": 0,
                        "pending_kgs": 0,
                        "remark": workorder.remarks,
                        "total_kgs": 0,
                    }
                    full_data.append(row)
                    continue

                for detail in details:

                    die = detail.die_profile

                    dispatched = BundleInward.objects.filter(
                        workorder_detail=detail,
                        status="Dispatched",
                        is_warehouse=False,
                        deleted=False,
                    ).aggregate(pcs=Sum("pieces"), kgs=Sum("weight"))

                    packed = BundleInward.objects.filter(
                        workorder_detail=detail, status="Packed", deleted=False
                    ).aggregate(pcs=Sum("pieces"), kgs=Sum("weight"))

                    warehouse = BundleInward.objects.filter(
                        workorder_detail=detail,
                        status="Warehouse",
                        is_warehouse=True,
                        deleted=False,
                    ).aggregate(pcs=Sum("pieces"), kgs=Sum("weight"))

                    row = {
                        "workorder_no": f"{workorder.order_no} / {workorder.order_date.strftime('%d-%m-%Y')}",
                        "po_no": f"{workorder.purchase_order_no} / {workorder.purchase_order_date.strftime('%d-%m-%Y') if workorder.purchase_order_date else ''}",
                        "workorder_detail_id": detail.id,
                        "is_priority": detail.is_priority,
                        "section": die.die_number if die else None,
                        "profile_image": die.die_diagram if die else None,
                        "length": detail.length,
                        "customer_reference_number": detail.customer_reference_number,
                        "customer_name": (
                            workorder.bill_to.customer_name
                            if workorder.bill_to
                            else None
                        ),
                        "alloy_temper": (
                            f"{detail.alloy.alloy_code} ({detail.alloy.color_code}) / {detail.temper.temper_code_new}"
                            if detail.alloy and detail.temper
                            else None
                        ),
                        "order_pcs": detail.pieces or 0,
                        "order_kgs": f"{detail.net_weight : .3f}",
                        "dispatched_pcs": dispatched["pcs"] or 0,
                        "dispatched_kgs": dispatched["kgs"] or 0,
                        "packed_pcs": packed["pcs"] or 0,
                        "packed_kgs": packed["kgs"] or 0,
                        "warehouse_pcs": warehouse["pcs"] or 0,
                        "warehouse_kgs": warehouse["kgs"] or 0,
                        "pending_pcs": detail.pending_pieces or 0,
                        "pending_kgs": detail.pending_weight or 0,
                        "remark": workorder.remarks,
                        "total_kgs": float(total_kgs),
                    }

                    for key in summary:
                        if "kgs" in key:
                            summary[key] += Decimal(row[key])
                        else:
                            summary[key] += int(row[key])

                    full_data.append(row)

            return Response(
                {
                    "success": True,
                    "message": "Workorder report fetched successfully",
                    "data": full_data,
                    "total_summary": summary,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="add-to-priority")
    def add_to_priority(self, request):
        workorder_detail_ids = request.data.get("workorder_detail_ids", [])

        if not isinstance(workorder_detail_ids, list):
            return Response(
                {"status": 400, "message": "workorder_detail_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        details = WorkOrderDetail.objects.select_related("die_profile").filter(
            id__in=workorder_detail_ids
        )
        existing_ids = set(details.values_list("id", flat=True))
        missing_ids = list(set(workorder_detail_ids) - existing_ids)

        if missing_ids:
            return Response(
                {
                    "status": 400,
                    "message": f"WorkOrderDetail with id {missing_ids} do not exist.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending_details = details.filter(status="Pending")
        non_pending_details = details.exclude(status="Pending")

        pending_data = list(
            pending_details.values("id", "die_profile__die_number", "length")
        )
        skipped_data = list(
            non_pending_details.values(
                "id", "status", "die_profile__die_number", "length"
            )
        )

        updated_count = pending_details.update(
            is_priority=True,
            priority_added_at=timezone.now(),
            priority_added_by=request.user,
            priority_removed_at=None,
            priority_removed_by=None,
            status="In-Priority",
        )

        success_messages = [
            f"WorkOrderDetail with {detail['die_profile__die_number'] or 'N/A'} / {detail['length']} added to priority."
            for detail in pending_data
        ]
        skipped_messages = [
            f"WorkOrderDetail with {detail['die_profile__die_number'] or 'N/A'} / {detail['length']} cannot be added to priority because its status is {detail['status']}."
            for detail in skipped_data
        ]

        return Response(
            {
                "success": True,
                "added_to_priority": updated_count,
                "skipped_count": len(skipped_data),
                "success_messages": success_messages,
                "skipped_messages": skipped_messages,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="remove-from-priority")
    def remove_from_priority(self, request):
        workorder_detail_ids = request.data.get("workorder_detail_ids", [])

        if not isinstance(workorder_detail_ids, list):
            return Response(
                {"status": 400, "message": "workorder_detail_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_ids = WorkOrderDetail.objects.filter(
            id__in=workorder_detail_ids
        ).values_list("id", flat=True)
        missing_ids = list(set(workorder_detail_ids) - set(existing_ids))

        if missing_ids:
            return Response(
                {
                    "status": 400,
                    "message": f"WorkOrderDetail with id {missing_ids} do not exist.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = WorkOrderDetail.objects.filter(
            id__in=workorder_detail_ids
        ).update(
            is_priority=False,
            priority_removed_at=timezone.now(),
            priority_removed_by=request.user,
        )

        return Response(
            {
                "status": 200,
                "message": f"{updated_count} WorkOrderDetail removed from priority.",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="workorder-report")
    def report_by_customer_date(self, request):
        try:
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            search = request.query_params.get("search", "").strip().lower()

            workorders = (
                WorkOrder.objects.select_related("bill_to")
                .prefetch_related("workorder_detail_workorder")
                .exclude(deleted=True)
                .order_by("-id")
            )

            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end = datetime.strptime(end_date, "%Y-%m-%d").date()
                    workorders = workorders.filter(order_date__range=(start, end))
                except ValueError:
                    return Response(
                        {
                            "status": False,
                            "message": "Invalid date format. Use YYYY-MM-DD",
                            "data": [],
                        },
                        status=400,
                    )

            customer_dict = defaultdict(list)

            for wo in workorders:
                customer_name = wo.bill_to.customer_name if wo.bill_to else ""
                order_date = wo.order_date
                work_order_no = wo.order_no or ""

                total_net_weight = (
                    wo.workorder_detail_workorder.aggregate(
                        total_weight=Sum("net_weight")
                    )["total_weight"]
                    or 0
                )

                net_weight_str = f"{total_net_weight:.3f}"

                if search:
                    if (
                        search not in customer_name.lower()
                        and search not in str(order_date)
                        and search not in work_order_no.lower()
                        and search not in net_weight_str
                    ):
                        continue

                customer_dict[customer_name].append(
                    {
                        "order_date": order_date,
                        "work_order_no": work_order_no,
                        "net_weight": net_weight_str,
                    }
                )

            response_data = []
            for customer, orders in customer_dict.items():
                response_data.append({"customer_name": customer, "orders": orders})

            return Response(
                {
                    "status": True,
                    "message": "Work order report fetched successfully",
                    "data": response_data,
                }
            )

        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": f"Something went wrong: {str(e)}",
                    "data": [],
                },
                status=500,
            )

    @action(detail=False, methods=["get"], url_path="die-wise-workorder-report")
    def die_wise_report(self, request):
        try:
            customer_id = request.query_params.get("customer_id")
            die_id = request.query_params.get("die_id")
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            search = request.query_params.get("search")

            if not customer_id:
                return Response(
                    {"success": False, "message": "customer_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            filters = {
                "deleted": False,
                "workorder__deleted": False,
                "workorder__bill_to_id": customer_id,
            }

            if die_id:
                filters["die_profile_id"] = die_id

            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    end = datetime.strptime(end_date, "%Y-%m-%d")
                    filters["workorder__order_date__range"] = (start, end)
                except ValueError:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid date format. Use YYYY-MM-DD.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            queryset = (
                WorkOrderDetail.objects.filter(**filters)
                .exclude(workorder__status__iexact="Closed")
                .select_related("die_profile", "workorder")
                .order_by("die_profile_id", "workorder__order_no")
            )

            if search:
                queryset = queryset.filter(
                    Q(workorder__order_no__icontains=search)
                    | Q(workorder__purchase_order_no__icontains=search)
                    | Q(customer_reference_number__icontains=search)
                    | Q(die_profile__die_number__icontains=search)
                )

            queryset = queryset.order_by("die_profile_id", "workorder__order_no")

            die_map = {}

            for detail in queryset:
                die = detail.die_profile
                workorder = detail.workorder

                die_id = die.id if die else None
                if die_id not in die_map:
                    die_map[die_id] = {
                        "die_id": die_id,
                        "die_number": die.die_number if die else None,
                        "die_diagram": die.die_diagram if die else None,
                        "workorders": [],
                    }

                dispatched = BundleInward.objects.filter(
                    workorder_detail=detail,
                    status="Dispatched",
                    is_warehouse=False,
                    deleted=False,
                ).aggregate(pcs=Sum("pieces"), kgs=Sum("weight"))

                dispatched_pcs = dispatched["pcs"] or 0
                dispatched_kgs = dispatched["kgs"] or 0

                warehouse = BundleInward.objects.filter(
                    workorder_detail=detail,
                    status="Dispatched",
                    is_warehouse=True,
                    deleted=False,
                ).aggregate(pcs=Sum("pieces"), kgs=Sum("weight"))

                warehouse_pcs = warehouse["pcs"] or 0
                warehouse_kgs = warehouse["kgs"] or 0

                die_map[die_id]["workorders"].append(
                    {
                        "workorder_no": f"{workorder.order_no} / {(workorder.order_date.strftime('%d-%m-%Y') if workorder.order_date else '')}",
                        "po_no": f"{workorder.purchase_order_no} / {(workorder.purchase_order_date.strftime('%d-%m-%Y') if workorder.purchase_order_date else '')}",
                        "length": detail.length,
                        "customer_reference_number": detail.customer_reference_number,
                        "order_pcs": detail.pieces or 0,
                        "order_kgs": detail.net_weight or 0,
                        "packed_pcs": detail.packed_pieces or 0,
                        "packed_kgs": detail.packed_weight or 0,
                        "pending_pcs": detail.pending_pieces or 0,
                        "pending_kgs": detail.pending_weight or 0,
                        "dispatched_pcs": dispatched_pcs,
                        "dispatched_kgs": dispatched_kgs,
                        "warehouse_pcs": warehouse_pcs,
                        "warehouse_kgs": warehouse_kgs,
                        "remark": workorder.remarks,
                    }
                )

            return Response(
                {
                    "success": True,
                    "message": "Die wise report fetched successfully",
                    "data": list(die_map.values()),
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="active-customers")
    def get_customer_by_open_workorder(self, request):
        try:
            customer_qs = (
                Customer.objects.filter(
                    workorder_customer_bill_to__status__in=["Open"],
                    workorder_customer_bill_to__deleted=False,
                )
                .distinct()
                .order_by("customer_name")
            )

            search = request.query_params.get("search")

            if search:
                customer_qs = customer_qs.filter(Q(customer_name__icontains=search))

            customer_qs = customer_qs.order_by("customer_name")

            data = [
                {"id": customer.id, "customer_name": customer.customer_name}
                for customer in customer_qs
            ]

            return Response(
                {
                    "success": True,
                    "message": "Customers with Open Workorders fetched successfully",
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="active-dies")
    def get_dies_by_open_workorder(self, request):
        try:
            die_qs = (
                Die.objects.filter(
                    workorder_detail_die__workorder__status__in=["Open"],
                    workorder_detail_die__workorder__deleted=False,
                )
                .exclude(workorder_detail_die__status="Pending")
                .distinct()
                .order_by("die_number")
            )

            search = request.query_params.get("search")

            if search:
                die_qs = die_qs.filter(Q(die_number__icontains=search))

            die_qs = die_qs.order_by("die_number")

            data = [
                {
                    "id": die.id,
                    "die_number": die.die_number,
                    "customer_reference_number": die.customer_reference_number,
                }
                for die in die_qs
            ]

            return Response(
                {
                    "success": True,
                    "message": "Dies with Open Workorders fetched successfully",
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="get-pending-workorders")
    def get_pending_workorders(self, request):
        try:
            status_value = request.query_params.get("status")
            search_query = request.query_params.get("search")

            workorders = (
                WorkOrder.objects.filter(
                    workorder_detail_workorder__packed_pieces__gt=0
                )
                .distinct()
                .order_by("-id")
            )

            if status_value:
                workorders = workorders.filter(status=status_value)

            if search_query:
                workorders = workorders.filter(
                    Q(order_no__icontains=search_query)
                    | Q(project_name__icontains=search_query)
                    | Q(bill_to__customer_name__icontains=search_query)
                )

            workorders = workorders.prefetch_related(
                Prefetch(
                    "workorder_detail_workorder",
                    queryset=WorkOrderDetail.objects.filter(packed_pieces__gt=0),
                    to_attr="packed_details",
                )
            )

            page = self.paginate_queryset(workorders)
            if page is not None:
                data = []
                for wo in page:
                    wo_data = WorkOrderSerializers(wo).data
                    wo_data["work_order_details"] = WorkOrderDetailSerializers(
                        getattr(wo, "packed_details", []), many=True
                    ).data
                    data.append(wo_data)
                return self.get_paginated_response(data)

            response_data = []
            for wo in workorders:
                wo_data = WorkOrderSerializers(wo).data
                wo_data["work_order_details"] = WorkOrderDetailSerializers(
                    getattr(wo, "packed_details", []), many=True
                ).data
                response_data.append(wo_data)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )