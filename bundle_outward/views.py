import logging
from collections import defaultdict
from datetime import datetime
from operator import itemgetter

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from bundle_inward.models import BundleInward
from bundle_outward.models import BundleOutward
from bundle_outward.serializers import BundleOutwardSerializer
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from customer.models import Customer
from utils.error_handling import custom_exception
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from workorder.models import WorkOrder, WorkOrderDetail

logger = logging.getLogger("file")


def get_outward_bundle_ids_for_outward(obj):
    try:
        return list(obj.outward_bundles.values_list("id", flat=True))
    except Exception:
        return []


def get_finalized_bundle_ids_for_outward(obj):
    try:
        return list(obj.finalized_bundles.values_list("id", flat=True))
    except Exception:
        return []


class BundleOutwardViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = BundleOutward.objects.filter(deleted=False)
    serializer_class = BundleOutwardSerializer

    def get_queryset(self):
        qs = (
            BundleOutward.objects.filter(deleted=False)
            .select_related(
                "vehicle_no",
                "created_by",
                "updated_by",
                "deleted_by",
                "workorder",
                "customer",
            )
            .prefetch_related("finalized_bundles", "outward_bundles")
            .order_by("-id")
        )
        dispatch_to = self.request.query_params.get("dispatch_to")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        filters = Q()

        if dispatch_to:
            filters &= Q(dispatch_to__icontains=dispatch_to)

        date_format = "%d-%m-%Y"
        try:
            if start_date:
                start_date_obj = datetime.strptime(start_date, date_format)
                start_date_obj = timezone.make_aware(
                    start_date_obj, timezone.get_current_timezone()
                )
                filters &= Q(created_at__gte=start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, date_format)
                end_date_obj = timezone.make_aware(
                    end_date_obj, timezone.get_current_timezone()
                )
                filters &= Q(created_at__lte=end_date_obj)
        except ValueError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Date format must be DD-MM-YYYY.")

        return qs.filter(filters)

    search_fields = [
        "workorder__order_no",
        "customer__customer_name",
        "slip_no",
        "vehicle_no__vehicle_no",
        "vehicle_no_display",
        "date_prepared",
        "shift",
        "vehicle_no",
        "dispatch_to",
        "remarks",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "id",
        "workorder__order_no",
        "customer__customer_name",
        "slip_no",
        "vehicle_no",
        "date_prepared",
        "shift",
        "vehicle_no",
        "dispatch_to",
        "created_by__first_name",
        "created_by__last_name",
    ]

    def _get_outward_bundle_ids(self, obj):
        """Return list of outward bundle ids for a BundleOutward instance.
        Reads the ManyToMany relation `outward_bundles`. Returns an empty
        list if the relation is not present or an error occurs.
        """
        try:
            return list(obj.outward_bundles.values_list("id", flat=True))
        except Exception:
            return []

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            slip_no = instance.slip_no
            bundle_ids = list(instance.outward_bundles.values_list("id", flat=True))

            if bundle_ids:
                bundles = BundleInward.objects.filter(id__in=bundle_ids).select_related(
                    "workorder_detail__die_profile",
                    "workorder_detail__alloy",
                    "workorder_detail__temper",
                    "workorder_detail__workorder",
                )

                dispatched_bundles = bundles.filter(status="Dispatched")
                if dispatched_bundles.exists():
                    grouped_data = defaultdict(
                        lambda: {
                            "bundles": [],
                            "workorder_no": "",
                            "item_description": "",
                        }
                    )

                    for bundle in dispatched_bundles:
                        detail = bundle.workorder_detail
                        workorder = detail.workorder
                        alloy_value = detail.alloy.alloy_code if detail.alloy else "N/A"
                        temper_value = detail.temper.name if detail.temper else "N/A"

                        item_description = f"{workorder.order_no} | {detail.die_profile.die_number} | {detail.length} mm | {detail.packed_weight} kg | {detail.dispatched_weight} kg | {detail.net_weight} kg | {alloy_value} | {temper_value}"

                        key = (workorder.id, detail.id)
                        grouped_data[key]["workorder_no"] = workorder.order_no
                        grouped_data[key]["item_description"] = item_description
                        grouped_data[key]["bundles"].append(bundle.bundle_no)

                    dispatch_message = [
                        f"{data['workorder_no']} - {data['item_description']}: {len(data['bundles'])} bundle(s) already dispatched"
                        for data in grouped_data.values()
                    ]

                    return Response(
                        {"success": False, "message": dispatch_message},
                        status=status.HTTP_200_OK,
                    )

            bundles.update(
                status="Packed",
                added_for_outword=False,
                is_warehouse=False,
                added_for_warehouse=False,
            )

            instance.deleted = True
            instance.save()

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="BundleOutward",
                description=f"Deleted BundlOutward {slip_no}",
                request=request,
            )

            logger.info("Record deleted successfully.")

            return Response(
                {"success": True, "message": "Record deleted successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error deleting BundleOutward: {str(e)}")
            return custom_exception(e)

    @action(detail=False, methods=["GET"], url_path="get-bundle-outward")
    def bundle_outward_summary(self, request):
        try:
            bundle_outward_id = request.query_params.get("bundle_outward_id")
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "-id")
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            reverse = ordering.startswith("-")
            ordering_field = ordering.lstrip("-")

            queryset = (
                BundleOutward.objects.filter(deleted=False)
                .select_related("workorder__bill_to")
                .all()
            )
            if bundle_outward_id:
                queryset = queryset.filter(id=bundle_outward_id)

            date_format = "%d-%m-%Y"
            if start_date:
                start_date_obj = datetime.strptime(start_date, date_format)
                queryset = queryset.filter(created_at__date__gte=start_date_obj.date())
            if end_date:
                end_date_obj = datetime.strptime(end_date, date_format)
                queryset = queryset.filter(created_at__date__lte=end_date_obj.date())

            all_bundle_ids = set()
            outward_map = {}
            for obj in queryset:
                bundle_ids = list(obj.outward_bundles.values_list("id", flat=True))
                outward_map[obj.id] = bundle_ids
                all_bundle_ids.update(bundle_ids)

            bundles_qs = BundleInward.objects.filter(id__in=all_bundle_ids)
            bundles_map = defaultdict(list)
            for b in bundles_qs:
                bundles_map[b.id] = b

            results = []
            for obj in queryset:
                bundle_ids = outward_map.get(obj.id, [])
                bundles = [
                    bundles_map[b_id] for b_id in bundle_ids if b_id in bundles_map
                ]

                total_weight = sum(b.weight or 0 for b in bundles)
                total_pieces = sum(b.pieces or 0 for b in bundles)
                total_bundles = len(bundles)

                data = {
                    "id": obj.id,
                    "work_order_id": obj.workorder.id,
                    "work_order_number": obj.workorder.order_no,
                    "order_date": obj.workorder.order_date,
                    "purchase_order_number": obj.workorder.purchase_order_no,
                    "purchase_order_date": obj.workorder.purchase_order_date,
                    "customer_name": (
                        obj.workorder.bill_to.customer_name
                        if obj.workorder.bill_to
                        else ""
                    ),
                    "date_prepared": obj.created_at,
                    "shift": obj.shift.shift_name,
                    "vehicle_details": {
                        "vehicle_id": obj.vehicle_no.id if obj.vehicle_no else None,
                        "vehicle_no": (
                            obj.vehicle_no.vehicle_no if obj.vehicle_no else None
                        ),
                        "transporter_name": (
                            obj.vehicle_no.party_name.party_name
                            if obj.vehicle_no and obj.vehicle_no.party_name
                            else None
                        ),
                    },
                    "slip_no": obj.slip_no,
                    "total_weight": f"{total_weight:.3f}",
                    "total_pieces": int(total_pieces),
                    "total_bundles": total_bundles,
                    "packing_mode_details": [
                        {"id": pm.id, "name": pm.name}
                        for pm in obj.workorder.packing_mode.all()
                    ],
                    "status": obj.dispatch_to,
                    "approved": obj.approved,
                    "remarks": obj.remarks,
                }
                if search_query:
                    if not any(
                        search_query in str(value).lower() for value in data.values()
                    ):
                        continue

                results.append(data)

            try:
                results = sorted(
                    results, key=itemgetter(ordering_field), reverse=reverse
                )
            except KeyError:
                pass

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(results, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "message": "Bundle outward summary retrieved successfully",
                    "data": paginated_data,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            data = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in request.data.items()
            }
            required_fields = [
                "workorder",
                "shift",
            ]

            for field in required_fields:
                if field not in data or not data[field]:
                    return Response(
                        {"success": False, "message": f"{field} is a required field."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            workorder = WorkOrder.objects.filter(id=data["workorder"]).first()
            if not workorder:
                return Response(
                    {"success": False, "message": "Invalid WorkOrder ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            customer = (
                Customer.objects.filter(id=data.get("customer")).first()
                if data.get("customer")
                else None
            )

            validated_data = {
                "workorder": workorder.id,
                "customer": customer,
                "shift": data["shift"],
                "vehicle_no": data.get("vehicle_no"),
                "dispatch_to": data.get("dispatch_to"),
                "remarks": data.get("remarks"),
                "created_by": request.user,
                "created_at": timezone.now(),
                "updated_at": None,
            }

            serializer = BundleOutwardSerializer(data=validated_data)
            if serializer.is_valid():
                bundle_outward_instance = serializer.save()

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="BundleOutward",
                    description=f"Created BundlOutward {bundle_outward_instance.slip_no}",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {
                        "success": True,
                        "data": {
                            "id": bundle_outward_instance.id,
                            "workorder": workorder.id,
                            "shift": bundle_outward_instance.shift.id,
                            "vehicle_no": bundle_outward_instance.vehicle_no_id,
                            "remarks": bundle_outward_instance.remarks,
                            "slip_no": bundle_outward_instance.slip_no,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True)

            if serializer.is_valid(raise_exception=True):
                instance = serializer.save(updated_by=request.user)

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="BundleOutward",
                    description=f"Updated BundlOutward {instance.slip_no}",
                    request=request,
                    payload=payload,
                )

                logger.info("Record updated successfully.")

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )

            else:
                logger.error(f"Error in updating record : {serializer.errors}")
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return custom_exception(e)

    @action(detail=True, methods=["GET"], url_path="bundle-outward-by-workorder")
    def bundle_outward_by_workorder(self, request, pk=None, *args, **kwargs):
        try:
            bundles = self.queryset.filter(workorder_id=pk)
            paginator = self.pagination_class()
            paginated_bundles = paginator.paginate_queryset(bundles, request)

            serializer = self.serializer_class(paginated_bundles, many=True)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "data": serializer.data,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=False,
        methods=["get"],
        url_path="workorder-detail-by-workorder-id/(?P<workorder_id>[^/.]+)",
    )
    def get_workorder_detail(self, request, workorder_id=None):
        try:
            outward_id = request.query_params.get("outward_id")

            workorder = WorkOrder.objects.filter(id=workorder_id).first()
            if not workorder:
                return Response(
                    {"success": False, "message": "Work order not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            excluded_bundle_ids = []

            if outward_id:
                outward_record = BundleOutward.objects.filter(id=outward_id).first()
                if not outward_record:
                    return Response(
                        {"success": False, "message": "Invalid outward_id provided."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if str(outward_record.workorder.id) != str(workorder_id):
                    return Response(
                        {
                            "success": False,
                            "message": "Work order mismatch for outward_id.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                all_outwards = BundleOutward.objects.filter(
                    workorder_id=workorder_id
                ).exclude(id=outward_id)

                for outward in all_outwards:
                    bundle_ids = outward.outward_bundles.values_list("id", flat=True)
                    excluded_bundle_ids.extend(list(bundle_ids))

            workorder_details = WorkOrderDetail.objects.filter(
                workorder=workorder
            ).exclude(status__in=["Dispatched", "Pending"])

            if not workorder_details.exists():
                return Response(
                    {
                        "success": False,
                        "message": "No details found for this work order.",
                    },
                    status=status.HTTP_204_NO_CONTENT,
                )

            filtered_details = []

            for detail in workorder_details:
                alloy_value = detail.alloy.alloy_code if detail.alloy else "N/A"
                temper_value = detail.temper.temper_code_new if detail.temper else "N/A"

                item_description = (
                    f"{workorder.order_no} | {detail.die_profile.die_number} | "
                    f"{detail.length} mm | {detail.packed_weight} kg | {detail.dispatched_weight} kg | "
                    f"{detail.net_weight} kg | {alloy_value} | {temper_value}"
                )

                all_bundles = BundleInward.objects.filter(
                    workorder_detail=detail, status="Packed", is_excess_stock=False
                ).exclude(id__in=excluded_bundle_ids)

                total_bundles = all_bundles.count()
                total_pieces = sum(b.pieces for b in all_bundles)
                total_weight = sum(b.weight for b in all_bundles)

                ready_bundles = all_bundles.filter(added_for_outword=False)
                ready_count = ready_bundles.count()
                ready_pieces = sum(b.pieces for b in ready_bundles)
                ready_weight = sum(b.weight for b in ready_bundles)

                added_bundles = all_bundles.filter(added_for_outword=True)
                added_count = added_bundles.count()
                added_pieces = sum(b.pieces for b in added_bundles)
                added_weight = sum(b.weight for b in added_bundles)

                if not any(
                    [
                        total_bundles,
                        total_pieces,
                        total_weight,
                        added_count,
                        added_pieces,
                        added_weight,
                        ready_count,
                        ready_pieces,
                        ready_weight,
                    ]
                ):
                    continue

                filtered_details.append(
                    {
                        "workorder_id": workorder.id,
                        "workorder_no": workorder.order_no,
                        "order_date": workorder.order_date,
                        "purchase_order_number": workorder.purchase_order_no,
                        "purchase_order_date": workorder.purchase_order_date,
                        "customer_name": workorder.bill_to.customer_name,
                        "workorder_detail_id": detail.id,
                        "item_description": item_description,
                        "total_bundle": total_bundles,
                        "total_piece": total_pieces,
                        "total_weight": f"{total_weight:.3f}",
                        "added_bundles": added_count,
                        "added_bundles_pieces": added_pieces,
                        "added_bundles_weight": f"{added_weight:.3f}",
                        "ready_bundles": ready_count,
                        "ready_bundles_pieces": ready_pieces,
                        "ready_bundles_weight": f"{ready_weight:.3f}",
                        "status": detail.status,
                    }
                )

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(filtered_details, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "data": paginated_data,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=500,
            )

    @action(detail=True, methods=["get"], url_path="bundle-inward-by-workorder-details")
    def get_bundles_by_workorder_detail(self, request, pk=None):
        try:
            if not pk:
                return Response(
                    {
                        "success": False,
                        "message": "workorder_detail_id is required in the URL",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            added_param = request.query_params.get("added", None)
            outward_id = request.query_params.get("outward_id", None)

            if added_param not in ["True", "False", None]:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid value for 'added'. Use 'True' or 'False'.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            added_filter = (
                True
                if added_param == "True"
                else False if added_param == "False" else None
            )

            workorder_detail = WorkOrderDetail.objects.filter(id=pk).first()
            if not workorder_detail:
                return Response(
                    {"success": False, "message": "WorkOrderDetail not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            workorder = workorder_detail.workorder

            exclude_bundle_ids = []

            if workorder:
                other_outwards = BundleOutward.objects.filter(workorder=workorder)
                if outward_id:
                    other_outwards = other_outwards.exclude(id=outward_id)

                for outward in other_outwards:
                    bundle_ids = outward.outward_bundles.values_list("id", flat=True)
                    exclude_bundle_ids.extend(list(bundle_ids))

            base_qs = BundleInward.objects.filter(
                workorder_detail_id=pk, status="Packed", is_excess_stock=False
            ).exclude(id__in=exclude_bundle_ids).order_by("-id")

            bundles = base_qs
            if added_filter is not None:
                bundles = bundles.filter(added_for_outword=added_filter)

            search_param = request.query_params.get("search", None)
            if search_param:
                try:
                    decimal_value = float(search_param)
                    int_value = int(decimal_value)
                    bundles = bundles.filter(
                        Q(bundle_no__icontains=search_param)
                        | Q(length=decimal_value)
                        | Q(pieces=int_value)
                        | Q(weight=decimal_value)
                        | Q(added_for_outword=(search_param.lower() == "true"))
                    )
                except ValueError:
                    bundles = bundles.filter(Q(bundle_no__icontains=search_param))

            total_bundles = base_qs.count()
            total_pieces = sum(b.pieces for b in base_qs)
            total_weight = sum(b.weight for b in base_qs)

            ready_bundles = base_qs.filter(added_for_outword=False)
            ready_count = ready_bundles.count()
            ready_pieces = sum(b.pieces for b in ready_bundles)
            ready_weight = sum(b.weight for b in ready_bundles)

            added_bundles = base_qs.filter(added_for_outword=True)
            added_count = added_bundles.count()
            added_pieces = sum(b.pieces for b in added_bundles)
            added_weight = sum(b.weight for b in added_bundles)

            bundle_list = []
            profile_description = None

            for bundle in bundles:
                detail = bundle.workorder_detail
                die = detail.die_profile if detail else None

                if die:
                    dims = [
                        d
                        for d in [
                            die.dimension1,
                            die.dimension2,
                            die.dimension3,
                            die.dimension4,
                        ]
                        if d
                    ]
                    item_name = " X ".join(f"{d} MM" for d in dims)
                else:
                    item_name = "No Dimensions Available"

                if not profile_description:
                    profile_description = item_name

                profile = die.die_number if die else "No Profile"
                length = detail.length if detail else None
                avg_weight = (
                    float(bundle.weight) / bundle.pieces if bundle.pieces else 0
                )

                bundle_list.append(
                    {
                        "id": bundle.id,
                        "bundle_no": bundle.bundle_no,
                        "profile_description": item_name,
                        "profile": profile,
                        "length": length,
                        "pieces": bundle.pieces,
                        "weight": bundle.weight,
                        "avg_weight": round(avg_weight, 3),
                        "packing_date_time": bundle.packing_date,
                        "added_for_outword": bundle.added_for_outword,
                    }
                )

            paginator = Pagination()
            paginated_bundles = paginator.paginate_queryset(bundle_list, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "message": "Bundles retrieved successfully",
                    "data": {
                        "profile_description": profile_description
                        or "No Profile Description Available",
                        "total_bundles": total_bundles,
                        "total_pieces": total_pieces,
                        "total_weight": round(total_weight, 3),
                        "added_bundles": added_count,
                        "added_bundles_weight": round(added_weight, 3),
                        "added_bundles_pieces": added_pieces,
                        "ready_bundles": ready_count,
                        "ready_bundles_weight": round(ready_weight, 3),
                        "ready_bundles_pieces": ready_pieces,
                        "bundles": paginated_bundles,
                    },
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="add-item-by-bundle-id")
    def add_item_by_bundle_id(self, request, *args, **kwargs):
        """Update added_for_outword to True and retrieve bundle details based on bundle IDs from JSON payload"""

        bundle_ids = request.data.get("bundle_id", [])
        outward_id = request.data.get("outward_id", None)
        if outward_id:
            bundle_outward = BundleOutward.objects.filter(id=outward_id).first()
            if bundle_outward:
                qs = BundleInward.objects.filter(id__in=bundle_ids)
                if qs.exists():
                    bundle_outward.outward_bundles.add(*qs)

        if not bundle_ids:
            return Response(
                {
                    "success": False,
                    "message": "bundle_id list is required in the request body",
                },
                status=status.HTTP_200_OK,
            )

        if not isinstance(bundle_ids, list):
            return Response(
                {"success": False, "message": "bundle_id must be a list"},
                status=status.HTTP_200_OK,
            )

        bundles = BundleInward.objects.filter(pk__in=bundle_ids)

        if not bundles.exists():
            return Response(
                {
                    "success": False,
                    "message": "No bundles found for the given IDs",
                    "data": [],
                },
                status=status.HTTP_200_OK,
            )

        bundle_data = []
        for bundle in bundles:
            bundle.added_for_outword = True
            bundle.save()

            detail = bundle.workorder_detail
            die = detail.die_profile if detail else None

            if die:
                dimensions = [
                    die.dimension1,
                    die.dimension2,
                    die.dimension3,
                    die.dimension4,
                ]
                dimension_values = [f"{dim} MM" for dim in dimensions if dim]
                profile_description = " X ".join(dimension_values)
            else:
                profile_description = "No Dimensions Available"

            profile = die.die_number if die else "No Profile"

            length = detail.length if detail else None

            avg_weight = float(bundle.weight) / bundle.pieces if bundle.pieces else 0

            packing_date_time = (
                f"{bundle.packing_date} {bundle.created_at.strftime('%H:%M:%S')}"
                if bundle.created_at
                else bundle.packing_date
            )

            bundle_data.append(
                {
                    "id": bundle.id,
                    "bundle_no": bundle.bundle_no,
                    "profile_description": profile_description,
                    "profile": profile,
                    "length": length,
                    "pieces": bundle.pieces,
                    "weight": bundle.weight,
                    "avg_weight": avg_weight,
                    "packing_date_time": packing_date_time,
                    "added_for_outword": bundle.added_for_outword,
                }
            )

        paginator = self.pagination_class()
        paginated_bundles = paginator.paginate_queryset(bundle_data, request)

        return paginator.get_paginated_response(
            {
                "success": True,
                "message": "Add Item successfully",
                "data": paginated_bundles,
            }
        )

    @action(detail=False, methods=["post"], url_path="restore-item-by-bundle-id")
    def restore_item_by_bundle_id(self, request, *args, **kwargs):
        bundle_ids = request.data.get("bundle_id", [])
        outward_id = request.data.get("outward_id")

        if outward_id:
            try:
                bundle_outward = BundleOutward.objects.get(id=outward_id)
            except BundleOutward.DoesNotExist:
                return Response(
                    {"success": False, "message": "Invalid outward_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not bundle_ids:
                return Response(
                    {
                        "success": False,
                        "message": "bundle_id list is required with outward_id",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bundles_to_remove = BundleInward.objects.filter(id__in=bundle_ids)
            bundle_outward.outward_bundles.remove(*bundles_to_remove)

        if not bundle_ids:
            return Response(
                {
                    "success": False,
                    "message": "bundle_id list is required in the request body",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(bundle_ids, list):
            return Response(
                {"success": False, "message": "bundle_id must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bundles = BundleInward.objects.filter(pk__in=bundle_ids)
        if not bundles.exists():
            return Response(
                {"success": False, "message": "No bundles found for the given IDs"},
                status=status.HTTP_200_OK,
            )

        bundles.update(added_for_outword=False)

        bundle_data = []
        for bundle in bundles:
            detail = bundle.workorder_detail
            die = detail.die_profile if detail else None

            if die:
                dims = [
                    d
                    for d in [
                        die.dimension1,
                        die.dimension2,
                        die.dimension3,
                        die.dimension4,
                    ]
                    if d
                ]
                profile_description = " X ".join(f"{d} MM" for d in dims)
            else:
                profile_description = "No Dimensions Available"

            profile = die.die_number if die else "No Profile"
            length = detail.length if detail else None
            avg_weight = float(bundle.weight) / bundle.pieces if bundle.pieces else 0
            packing_date_time = (
                f"{bundle.packing_date} {bundle.created_at.strftime('%H:%M:%S')}"
                if bundle.packing_date and bundle.created_at
                else str(bundle.packing_date or "")
            )

            bundle_data.append(
                {
                    "id": bundle.id,
                    "bundle_no": bundle.bundle_no,
                    "profile_description": profile_description,
                    "profile": profile,
                    "length": length,
                    "pieces": bundle.pieces,
                    "weight": bundle.weight,
                    "avg_weight": avg_weight,
                    "packing_date_time": packing_date_time,
                    "added_for_outword": False,
                }
            )

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(bundle_data, request)

        return paginator.get_paginated_response(
            {
                "success": True,
                "message": "Restore Item successfully",
                "data": paginated_data,
            }
        )

    @action(detail=False, methods=["patch"], url_path="finalize-bundle")
    def finalize_bundle(self, request):
        try:
            workorder_detail_ids = request.data.get("workorder_detail_id", [])
            outward_id = request.data.get("outward_id")

            if not isinstance(workorder_detail_ids, list) or not all(
                isinstance(i, int) for i in workorder_detail_ids
            ):
                return Response(
                    {
                        "success": False,
                        "message": "workorder_detail_id must be a list of integers",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not workorder_detail_ids:
                return Response(
                    {
                        "success": False,
                        "message": "At least one workorder_detail_id is required",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not outward_id:
                return Response(
                    {"success": False, "message": "outward_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bundle_outward = BundleOutward.objects.filter(id=outward_id).first()
            if not bundle_outward:
                return Response(
                    {"success": False, "message": "BundleOutward not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            outward_bundle_ids = list(
                bundle_outward.outward_bundles.values_list("id", flat=True)
            )

            bundles_to_finalize = BundleInward.objects.filter(
                id__in=outward_bundle_ids,
                added_for_outword=True,
                status="Packed",
                workorder_detail_id__in=workorder_detail_ids,
            )

            if not bundles_to_finalize.exists():
                return Response(
                    {
                        "success": False,
                        "message": "No eligible bundles found to finalize",
                    },
                    status=status.HTTP_200_OK,
                )

            now = timezone.now()
            update_fields = {}
            if bundle_outward.dispatch_to == "Customer":
                update_fields["status"] = "Dispatched"
                update_fields["dispatch_date"] = now
            elif bundle_outward.dispatch_to == "Warehouse":
                update_fields["status"] = "Warehouse"
                update_fields["dispatch_date"] = None
                update_fields["is_warehouse"] = True

            updated_count = bundles_to_finalize.update(**update_fields)

            bundle_outward.finalized_bundles.add(*bundles_to_finalize)

            bundle_outward.dispatch_date = now
            if not bundle_outward.approved:
                bundle_outward.approved = True
            bundle_outward.save()

            for workorder_detail_id in workorder_detail_ids:
                total_dispatched_weight = (
                    BundleInward.objects.filter(
                        workorder_detail_id=workorder_detail_id,
                        status__in=["Dispatched", "Warehouse"],
                    ).aggregate(Sum("weight"))["weight__sum"]
                    or 0
                )
                total_dispatched_pieces = (
                    BundleInward.objects.filter(
                        workorder_detail_id=workorder_detail_id,
                        status__in=["Dispatched", "Warehouse"],
                    ).aggregate(Sum("pieces"))["pieces__sum"]
                    or 0
                )
                packed_weight = (
                    BundleInward.objects.filter(
                        workorder_detail_id=workorder_detail_id, status="Packed"
                    ).aggregate(Sum("weight"))["weight__sum"]
                    or 0
                )
                packed_pieces = (
                    BundleInward.objects.filter(
                        workorder_detail_id=workorder_detail_id, status="Packed"
                    ).aggregate(Sum("pieces"))["pieces__sum"]
                    or 0
                )

                WorkOrderDetail.objects.filter(id=workorder_detail_id).update(
                    dispatched_weight=total_dispatched_weight,
                    dispatched_pieces=total_dispatched_pieces,
                    packed_weight=packed_weight,
                    packed_pieces=packed_pieces,
                )

                workorder_detail = WorkOrderDetail.objects.get(id=workorder_detail_id)
                from utils.packing_tolerance import is_quantity_fulfilled

                if is_quantity_fulfilled(
                    total_dispatched_pieces,
                    total_dispatched_weight,
                    workorder_detail,
                ):
                    workorder_detail.status = "Dispatched"
                    workorder_detail.save()
                    try:
                        from workorder.process_tracking import advance_process

                        advance_process(
                            workorder_detail=workorder_detail,
                            stage="DISPATCHED",
                            user=request.user,
                            remarks="Bundle outward order qty fulfilled (WO tolerance applies to max allowed)",
                        )
                    except Exception:
                        pass

            workorder_ids = (
                WorkOrderDetail.objects.filter(id__in=workorder_detail_ids)
                .values_list("workorder_id", flat=True)
                .distinct()
            )

            for workorder_id in workorder_ids:
                total_details = WorkOrderDetail.objects.filter(
                    workorder_id=workorder_id
                ).count()
                dispatched_details = WorkOrderDetail.objects.filter(
                    workorder_id=workorder_id, status="Dispatched"
                ).count()
                if total_details > 0 and dispatched_details == total_details:
                    WorkOrder.objects.filter(id=workorder_id).update(
                        status="Dispatched"
                    )

            finalized_bundle_ids = list(
                bundles_to_finalize.values_list("id", flat=True)
            )

            log_user_activity(
                user=request.user,
                action="FINALIZE BUNDLE",
                module_name="BundleOutward",
                description=f"Finalized bundles: {finalized_bundle_ids}",
                request=request,
                payload=clean_payload(request.data),
            )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} bundle(s) finalized successfully",
                    "finalized_bundles_count": updated_count,
                    "finalized_bundle_ids": finalized_bundle_ids,
                    "approved": bundle_outward.approved,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error finalizing bundles: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": "An error occurred while finalizing bundles",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="packing-slip-summary")
    def packing_slip_summary(self, request):
        bundle_outward_id = request.query_params.get("bundle_outward_id")
        if not bundle_outward_id:
            return Response(
                {"status": False, "message": "bundle_outward_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            bundle_outward = BundleOutward.objects.get(id=bundle_outward_id)
        except BundleOutward.DoesNotExist:
            return Response(
                {"status": False, "message": "BundleOutward not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        workorder = bundle_outward.workorder
        workorder_details = WorkOrderDetail.objects.filter(workorder=workorder).exclude(
            status="Pending"
        )

        bundle_ids = list(bundle_outward.outward_bundles.values_list("id", flat=True))

        summary = []
        total_net_weight = 0
        total_gross_weight = 0
        total_pieces = 0
        total_bundles = 0

        for detail in workorder_details:
            dispatched_bundles = BundleInward.objects.filter(
                workorder_detail=detail, added_for_outword=True, id__in=bundle_ids
            )

            aggregates = dispatched_bundles.aggregate(
                total_net_weight=Sum("weight"),
                total_gross_weight=Sum("gross_weight"),
                total_pieces=Sum("pieces"),
            )

            bundle_count = dispatched_bundles.count()

            if (aggregates["total_pieces"] or 0) == 0 and bundle_count == 0:
                continue

            total_net_weight += aggregates["total_net_weight"] or 0
            total_gross_weight += aggregates["total_gross_weight"] or 0
            total_pieces += aggregates["total_pieces"] or 0
            total_bundles += bundle_count

            die = detail.die_profile
            die_dimensions = " x ".join(
                filter(
                    None,
                    [
                        str(die.dimension1) if die.dimension1 else "",
                        str(die.dimension2) if die.dimension2 else "",
                        str(die.dimension3) if die.dimension3 else "",
                        str(die.dimension4) if die.dimension4 else "",
                    ],
                )
            ).strip()

            alloy_name = detail.alloy.alloy_code if detail.alloy else ""
            temper_name = detail.temper.temper_code_new if detail.temper else ""
            alloy_temper = f"{alloy_name} - {temper_name}".strip(" -")

            net_wt = aggregates["total_net_weight"] or 0
            gross_wt = aggregates["total_gross_weight"] or 0
            pcs = aggregates["total_pieces"] or 0

            summary.append(
                {
                    "alloy & temper": alloy_temper,
                    "length": detail.length,
                    "die_number": die.die_number if die else None,
                    "die_diagram": die.die_diagram if die else None,
                    "die_dimensions": die_dimensions,
                    "total_net_weight": f"{net_wt:.3f}",
                    "total_gross_weight": f"{gross_wt:.3f}",
                    "total_pieces": pcs,
                    "total_bundles": bundle_count,
                }
            )
        customer = workorder.bill_to
        office_address = (
            ", ".join(
                filter(
                    None,
                    [
                        customer.office_address_shop,
                        customer.office_address_area,
                        customer.office_address_landmark,
                        customer.office_address_city,
                        customer.office_address_state,
                        customer.office_address_country,
                        customer.office_address_pin_code,
                    ],
                )
            )
            if customer
            else ""
        )

        factory_address = (
            ", ".join(
                filter(
                    None,
                    [
                        customer.factory_address_shop,
                        customer.factory_address_area,
                        customer.factory_address_landmark,
                        customer.factory_address_city,
                        customer.factory_address_state,
                        customer.factory_address_country,
                        customer.factory_address_pin_code,
                    ],
                )
            )
            if customer
            else ""
        )

        response_data = {
            "order_no": workorder.order_no,
            "packing_type": getattr(workorder, "packing_type", "") or "",
            "dispatched_date": bundle_outward.dispatch_date,
            "customer_name": customer.customer_name if customer else None,
            "phone_number": customer.phone_number if customer else None,
            "office_address": office_address,
            "factory_address": factory_address,
            "vehicle_details": {
                "vehicle_id": (
                    bundle_outward.vehicle_no_id if bundle_outward.vehicle_no else None
                ),
                "vehicle_no": (
                    bundle_outward.vehicle_no.vehicle_no
                    if bundle_outward.vehicle_no
                    else None
                ),
                "transporter_name": (
                    bundle_outward.vehicle_no.party_name.party_name
                    if bundle_outward.vehicle_no
                    and bundle_outward.vehicle_no.party_name
                    else None
                ),
            },
            "slip_no": bundle_outward.slip_no,
            "remarks": bundle_outward.remarks,
            "summary": summary,
            "total_summary": {
                "total_net_weight": f"{total_net_weight:.3f}",
                "total_gross_weight": f"{total_gross_weight:.3f}",
                "total_pieces": total_pieces,
                "total_bundles": total_bundles,
            },
        }

        return Response(
            {"status": True, "data": response_data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="packing-slip-bundles")
    def get_packing_slip_bundles(self, request):
        bundle_outward_id = request.query_params.get("bundle_outward_id")
        if not bundle_outward_id:
            return Response(
                {"success": False, "message": "bundle_outward_id is required"},
                status=400,
            )

        try:
            outward = BundleOutward.objects.select_related(
                "workorder", "workorder__bill_to"
            ).get(id=bundle_outward_id)
        except BundleOutward.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid bundle_outward_id"},
                status=404,
            )

        workorder = outward.workorder
        workorder_details = WorkOrderDetail.objects.filter(workorder=workorder)
        bundle_ids = list(outward.outward_bundles.values_list("id", flat=True))

        grouped_bundles = {}
        total_pieces = 0
        total_net_weight = 0.0
        total_gross_weight = 0.0

        for detail in workorder_details:
            bundles = BundleInward.objects.filter(
                workorder_detail=detail,
                added_for_outword=True,
                id__in=bundle_ids,
            )

            section = str(detail.die_profile.die_number or "N/A")
            length = float(detail.length or 0.0)
            group_key = (section, length)

            for bundle in bundles:
                die = detail.die_profile
                die_dimensions = " x ".join(
                    filter(
                        None,
                        [
                            str(die.dimension1) if die.dimension1 else "",
                            str(die.dimension2) if die.dimension2 else "",
                            str(die.dimension3) if die.dimension3 else "",
                            str(die.dimension4) if die.dimension4 else "",
                        ],
                    )
                ).strip()

                pieces_num = bundle.pieces or 0
                net_wt_num = float(bundle.weight or 0)
                gross_wt_num = float(bundle.gross_weight or 0)

                data = {
                    "type": "data",
                    "bundle_no": bundle.bundle_no,
                    "die_number": die.die_number,
                    "die_diagram": die.die_diagram,
                    "die_dimensions": die_dimensions,
                    "length": length,
                    "pieces": pieces_num,
                    "net_weight": f"{net_wt_num:.3f}",
                    "gross_weight": f"{gross_wt_num:.3f}",
                    "_calc_pieces": pieces_num,
                    "_calc_net": net_wt_num,
                    "_calc_gross": gross_wt_num,
                }

                grouped_bundles.setdefault(group_key, []).append(data)
        final_bundle_list = []
        total_data_count = 0

        for (section, length), bundle_group in grouped_bundles.items():
            group_pieces = 0
            group_net = 0.0
            group_gross = 0.0

            for bundle in bundle_group:
                display_bundle = {
                    k: v for k, v in bundle.items() if not k.startswith("_")
                }
                final_bundle_list.append(display_bundle)

                group_pieces += bundle["_calc_pieces"]
                group_net += bundle["_calc_net"]
                group_gross += bundle["_calc_gross"]
                total_pieces += bundle["_calc_pieces"]
                total_net_weight += bundle["_calc_net"]
                total_gross_weight += bundle["_calc_gross"]

            total_data_count += len(bundle_group)

            final_bundle_list.append(
                {
                    "type": "subtotal",
                    "description": f"{len(bundle_group)} Bundles",
                    "pieces": group_pieces,
                    "net_weight_kg": f"{group_net:.3f}",
                    "gross_weight_kg": f"{group_gross:.3f}",
                }
            )
        customer = workorder.bill_to
        office_address = (
            ", ".join(
                filter(
                    None,
                    [
                        customer.office_address_shop,
                        customer.office_address_area,
                        customer.office_address_landmark,
                        customer.office_address_city,
                        customer.office_address_state,
                        customer.office_address_country,
                        customer.office_address_pin_code,
                    ],
                )
            )
            if customer
            else ""
        )

        factory_address = (
            ", ".join(
                filter(
                    None,
                    [
                        customer.factory_address_shop,
                        customer.factory_address_area,
                        customer.factory_address_landmark,
                        customer.factory_address_city,
                        customer.factory_address_state,
                        customer.factory_address_country,
                        customer.factory_address_pin_code,
                    ],
                )
            )
            if customer
            else ""
        )

        response = {
            "success": True,
            "data": {
                "order_no": workorder.order_no,
                "packing_type": getattr(workorder, "packing_type", "") or "",
                "dispatched_date": outward.dispatch_date,
                "vehicle_details": {
                    "vehicle_id": outward.vehicle_no_id if outward.vehicle_no else None,
                    "vehicle_no": (
                        outward.vehicle_no.vehicle_no if outward.vehicle_no else None
                    ),
                    "transporter_name": (
                        outward.vehicle_no.party_name.party_name
                        if outward.vehicle_no and outward.vehicle_no.party_name
                        else None
                    ),
                },
                "slip_no": outward.slip_no,
                "remarks": outward.remarks,
                "customer_name": customer.customer_name if customer else None,
                "phone_number": customer.phone_number if customer else None,
                "office_address": office_address,
                "factory_address": factory_address,
                "bundles": final_bundle_list,
                "summary": {
                    "description": f"{total_data_count} Bundles",
                    "total_pieces": total_pieces,
                    "total_net_weight": f"{total_net_weight:.3f}",
                    "total_gross_weight": f"{total_gross_weight:.3f}",
                },
            },
        }

        return Response(response, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="dispatch-report")
    def dispatch_report(self, request):
        try:
            shift = request.query_params.get("shift", "").upper()
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")

            filters = Q(deleted=False) & Q(dispatch_to="Customer")

            if from_date and to_date:
                try:
                    start = datetime.strptime(from_date, "%Y-%m-%d")
                    end = datetime.strptime(to_date, "%Y-%m-%d")
                    filters &= Q(
                        date_prepared__date__gte=start, date_prepared__date__lte=end
                    )
                except ValueError:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid date format. Use YYYY-MM-DD",
                            "data": [],
                        },
                        status=400,
                    )

            if shift in ["A", "B"]:
                filters &= Q(shift=shift)

            outward_qs = (
                BundleOutward.objects.filter(filters)
                .annotate(prepared_date=TruncDate("date_prepared"))
                .order_by("prepared_date")
            )

            date_map = {}

            for outward in outward_qs:
                prepared_date = getattr(outward, "prepared_date")
                if not prepared_date:
                    continue

                date_str = prepared_date.strftime("%Y-%m-%d")

                bundle_ids = outward.outward_bundles.filter(deleted=False).values_list(
                    "id", flat=True
                )

                total_weight = (
                    BundleInward.objects.filter(
                        id__in=bundle_ids, deleted=False
                    ).aggregate(total=Sum("weight"))["total"]
                    or 0
                )
                total_weight = round(float(total_weight), 2)

                if date_str not in date_map:
                    date_map[date_str] = {"shift_a": 0.0, "shift_b": 0.0}

                if outward.shift == "A":
                    date_map[date_str]["shift_a"] += total_weight
                elif outward.shift == "B":
                    date_map[date_str]["shift_b"] += total_weight
            data = []
            for date, weights in sorted(date_map.items()):
                a = round(weights["shift_a"], 2)
                b = round(weights["shift_b"], 2)
                total = round(a + b, 2)

                if shift == "A":
                    data.append(
                        {"date": date, "shift_a": f"{a:.2f}", "total": f"{a:.2f}"}
                    )
                elif shift == "B":
                    data.append(
                        {"date": date, "shift_b": f"{b:.2f}", "total": f"{b:.2f}"}
                    )
                else:
                    data.append(
                        {
                            "date": date,
                            "shift_a": f"{a:.2f}",
                            "shift_b": f"{b:.2f}",
                            "total": f"{total:.2f}",
                        }
                    )

            grand_total = round(sum(float(item["total"]) for item in data), 2)

            return Response(
                {
                    "success": True,
                    "message": "Customer dispatch report fetched successfully",
                    "data": data,
                    "grand_total": f"{grand_total:.2f}",
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "data": [],
                },
                status=500,
            )
