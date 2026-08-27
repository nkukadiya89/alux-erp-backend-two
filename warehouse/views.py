import logging
from datetime import datetime
from operator import itemgetter

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from bundle_inward.models import BundleInward
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from utils.error_handling import custom_exception
from utils.generate_number import generate_warehouse_slip_no
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination
from warehouse.models import Warehouse, WarehouseBundleInward, WarehouseBundleOutward
from warehouse.serializers import WarehouseSerializers
from workorder.models import WorkOrder, WorkOrderDetail
from workorder.serializers import WorkOrderSerializers

logger = logging.getLogger("file")


class WarehouseViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = Warehouse.objects.all().order_by("-id")
    serializer_class = WarehouseSerializers

    search_fields = [
        "id",
        "workorder__order_no",
        "vehicle_no__vehicle_no",
        "remarks",
        "dispatched_to_customer_date",
        "dispatched",
        "added_for_outword",
        "created_by_name",
        "updated_by_name",
        "deleted_by_name",
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
    ]

    ordering_fields = [
        "id",
        "workorder__order_no",
        "vehicle_no",
        "remarks",
        "dispatched_to_customer_date",
        "dispatched",
        "added_for_outword",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date or end_date:
            try:
                if start_date:
                    sdate = datetime.strptime(start_date, "%d-%m-%Y").date()
                    queryset = queryset.filter(created_at__date__gte=sdate)

                if end_date:
                    edate = datetime.strptime(end_date, "%d-%m-%Y").date()
                    queryset = queryset.filter(created_at__Date__gte=edate)
            except ValueError:
                raise ValidationError("Date format must be DD-MM-YYYY")

        return queryset.select_related(
            "vehicle_no",
            "workorder",
            "created_by",
            "updated_by",
            "deleted_by",
        ).order_by("-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        try:
            fields_param = request.query_params.get("fields")
            if fields_param and fields_param.strip():
                requested_fields = [
                    f.strip() for f in fields_param.split(",") if f.strip()
                ]
                valid_fields = []

                for field in requested_fields:
                    try:
                        queryset.values(field)
                        valid_fields.append(field)
                    except Exception:
                        continue

                if valid_fields:
                    queryset = queryset.values(*valid_fields)

                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        return self.get_paginated_response(
                            {"success": True, "data": list(page)}
                        )

                    return Response(
                        {"success": True, "data": list(queryset)},
                        status=status.HTTP_200_OK,
                    )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.serializer_class(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return custom_exception(e)

    @action(detail=False, methods=["GET"], url_path="get-warehouse-outward")
    def warehouse_outward_summary(self, request):
        try:
            warehouse_id = request.query_params.get("warehouse_id")
            outward_id = request.query_params.get("outward_id")
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "-id")
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")

            reverse = ordering.startswith("-")
            order_key = ordering.lstrip("-") if reverse else ordering

            queryset = (
                Warehouse.objects.filter(deleted=False)
                .select_related("workorder", "workorder__bill_to")
                .prefetch_related("outward_bundles")
                .all()
            )

            if warehouse_id:
                queryset = queryset.filter(id=warehouse_id)
            if outward_id:
                queryset = queryset.filter(id=outward_id)

            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, "%d-%m-%Y")
                    queryset = queryset.filter(
                        created_at__date__gte=start_date_obj.date()
                    )
                except ValueError:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid start_date format. Use DD-MM-YYYY.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, "%d-%m-%Y")
                    queryset = queryset.filter(
                        created_at__date__lte=end_date_obj.date()
                    )
                except ValueError:
                    return Response(
                        {
                            "success": False,
                            "message": "Invalid end_date format. Use DD-MM-YYYY.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            results = []

            for obj in queryset:
                bundles = obj.outward_bundles.all()

                total_weight = sum(float(b.weight or 0) for b in bundles)
                total_pieces = sum(b.pieces or 0 for b in bundles)
                total_bundles = bundles.count()

                data = {
                    "id": obj.id,
                    "work_order_id": obj.workorder.id if obj.workorder else None,
                    "work_order_number": (
                        obj.workorder.order_no if obj.workorder else ""
                    ),
                    "order_date": obj.workorder.order_date if obj.workorder else None,
                    "purchase_order_number": (
                        obj.workorder.purchase_order_no if obj.workorder else ""
                    ),
                    "purchase_order_date": (
                        obj.workorder.purchase_order_date if obj.workorder else None
                    ),
                    "shift" : obj.shift.shift_name if obj.shift else None,
                    "customer_name": (
                        obj.workorder.bill_to.customer_name
                        if obj.workorder and obj.workorder.bill_to
                        else ""
                    ),
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
                    "date_prepared": obj.created_at,
                    "packing_mode_details": [
                        {"id": pm.id, "name": pm.name}
                        for pm in obj.workorder.packing_mode.all()
                    ],
                    "total_weight": round(total_weight, 3),
                    "total_pieces": total_pieces,
                    "total_bundles": total_bundles,
                    "slip_no": obj.slip_no or "",
                    "approved": obj.dispatched if hasattr(obj, "dispatched") else False,
                    "remarks": obj.remarks or "",
                }

                if search_query:
                    if not any(
                        search_query in str(value).lower()
                        for value in data.values()
                        if value is not None
                    ):
                        continue

                results.append(data)

            if order_key in [
                "id",
                "total_weight",
                "total_pieces",
                "total_bundles",
                "date_prepared",
                "customer_name",
            ]:
                results = sorted(results, key=itemgetter(order_key), reverse=reverse)

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(results, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "message": "Warehouse outward summary retrieved successfully",
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
            required_fields = ["workorder"]

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

            validated_data = {
                "workorder": workorder.id,
                "vehicle_no": data.get("vehicle_no"),
                "remarks": data.get("remarks"),
                "shift": data.get("shift"),
                "created_by": request.user,
                "created_at": timezone.now(),
                "updated_at": None,
                "dispatched_to_customer_date": None,
                "outward_bundle_ids": data.get("outward_bundle_ids", []),
                "finalized_bundle_ids": data.get("finalized_bundle_ids", []),
            }

            serializer = self.serializer_class(
                data=validated_data, context={"request": request}
            )
            if serializer.is_valid():
                warehouse_instance = serializer.save()
                warehouse_instance.slip_no = generate_warehouse_slip_no()
                warehouse_instance.save(update_fields=["slip_no"])

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="Warehouse BundleOutward",
                    description=f"Created WareHouse BundlOutward {warehouse_instance.slip_no}",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {
                        "success": True,
                        "data": {
                            "id": warehouse_instance.id,
                            "workorder": str(workorder),
                            "vehicle_no": warehouse_instance.vehicle_no_id,
                            "remarks": warehouse_instance.remarks,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                logger.error(
                    f"Validation error while creating warehouse outward: {serializer.errors}"
                )
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.exception("Exception while creating warehouse outward record")
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_at"] = timezone.now()
        data["approved_at"] = None

        try:
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=data, partial=True, context={"request": request}
            )

            if serializer.is_valid():
                instance = serializer.save(updated_by=self.request.user)

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="Warehouse BundleOutward",
                    description=f"Updated WareHouse BundlOutward {instance.slip_no}",
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

    @action(detail=False, methods=["GET"], url_path="get-workorder")
    def get_workorder(self, request, pk=None, *args, **kwargs):
        """
        Retrieve a list of WorkOrders that have WorkOrderDetails with dispatched bundles in the warehouse.
        """
        try:
            dispatched_workorder_ids = (
                BundleInward.objects.filter(
                    status="Dispatched", is_warehouse=True, deleted=False
                )
                .values_list("workorder_id", flat=True)
                .distinct()
            )

            workorders = WorkOrder.objects.filter(
                id__in=dispatched_workorder_ids, deleted=False
            ).order_by("-id")

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(workorders, request)
            serializer = WorkOrderSerializers(page, many=True)

            return paginator.get_paginated_response(
                {"success": True, "data": serializer.data}
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
    def get_warehouse_workorder_detail(self, request, workorder_id=None):
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
                current_warehouse = Warehouse.objects.filter(id=outward_id).first()
                if not current_warehouse:
                    return Response(
                        {"success": False, "message": "Invalid outward_id provided."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if str(current_warehouse.workorder.id) != str(workorder_id):
                    return Response(
                        {
                            "success": False,
                            "message": "Work order mismatch for outward_id.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                all_warehouses = Warehouse.objects.filter(
                    workorder_id=workorder_id
                ).exclude(id=outward_id)
                for warehouse in all_warehouses:
                    bundle_ids = warehouse.outward_bundles.values_list("id", flat=True)
                    excluded_bundle_ids.extend(list(bundle_ids))

            valid_workorder_detail_ids = (
                BundleInward.objects.filter(
                    workorder=workorder,
                    status="Warehouse",
                    is_warehouse=True,
                    deleted=False,
                )
                .values_list("workorder_detail_id", flat=True)
                .distinct()
            )

            workorder_details = WorkOrderDetail.objects.filter(
                id__in=valid_workorder_detail_ids
            )

            if not workorder_details.exists():
                return Response(
                    {
                        "success": False,
                        "message": "No details found for this work order.",
                    },
                    status=status.HTTP_200_OK,
                )

            paginator = self.pagination_class()
            paginated_details = paginator.paginate_queryset(workorder_details, request)

            data = []
            for detail in paginated_details:
                alloy_value = detail.alloy.alloy_code if detail.alloy else "N/A"
                temper_value = detail.temper.temper_code_new if detail.temper else "N/A"

                item_description = (
                    f"{workorder.order_no} | {detail.die_profile.die_number} | "
                    f"{detail.length} mm | {detail.packed_weight} kg | {detail.dispatched_weight} kg | "
                    f"{detail.net_weight} kg | {alloy_value} | {temper_value}"
                )

                all_bundles = BundleInward.objects.filter(
                    workorder_detail=detail,
                    status="Warehouse",
                    is_warehouse=True,
                    deleted=False,
                ).exclude(id__in=excluded_bundle_ids)

                total_bundle = all_bundles.count()
                total_piece = sum(b.pieces for b in all_bundles)
                total_weight = sum(b.weight for b in all_bundles)

                added_bundles = all_bundles.filter(added_for_warehouse=False)
                ready_bundles = all_bundles.filter(added_for_warehouse=True)

                data.append(
                    {
                        "workorder_id": workorder.id,
                        "workorder_detail_id": detail.id,
                        "workorder_no": workorder.order_no,
                        "order_date": workorder.order_date,
                        "purchase_order_number": workorder.purchase_order_no,
                        "purchase_order_date": workorder.purchase_order_date,
                        "customer_name": workorder.bill_to.customer_name,
                        "item_description": item_description,
                        "total_bundle": total_bundle,
                        "total_piece": total_piece,
                        "total_weight": total_weight,
                        "ready_bundles": added_bundles.count(),
                        "ready_bundles_pieces": sum(b.pieces for b in added_bundles),
                        "ready_bundles_weight": sum(b.weight for b in added_bundles),
                        "added_bundles": ready_bundles.count(),
                        "added_bundles_pieces": sum(b.pieces for b in ready_bundles),
                        "added_bundles_weight": sum(b.weight for b in ready_bundles),
                        "status": detail.status,
                    }
                )

            return paginator.get_paginated_response({"success": True, "data": data})

        except Exception as e:
            return Response(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                    status=status.HTTP_200_OK,
                )

            added_param = request.query_params.get("added", None)
            outward_id = request.query_params.get("outward_id", None)

            if added_param not in ["True", "False", None]:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid value for 'added'. Use 'True' or 'False'.",
                    },
                    status=status.HTTP_200_OK,
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
                    status=status.HTTP_400_BAD_REQUEST,
                )
            workorder = workorder_detail.workorder

            exclude_bundle_ids = []
            if outward_id and workorder:
                other_warehouses = Warehouse.objects.filter(workorder=workorder)
                if outward_id:
                    other_warehouses = other_warehouses.exclude(id=outward_id)

                for warehouse in other_warehouses:
                    bundle_ids = warehouse.outward_bundles.values_list("id", flat=True)
                    exclude_bundle_ids.extend(bundle_ids)

            base_qs = BundleInward.objects.filter(
                workorder_detail_id=pk, status="Warehouse", is_warehouse=True
            ).exclude(id__in=exclude_bundle_ids)

            bundles = base_qs
            if added_filter is not None:
                bundles = bundles.filter(added_for_warehouse=added_filter)

            search_param = request.query_params.get("search", None)
            if search_param:
                try:
                    decimal_value = float(search_param)
                    bundles = bundles.filter(
                        Q(bundle_no__icontains=search_param)
                        | Q(length=decimal_value)
                        | Q(pieces=int(decimal_value))
                        | Q(weight=decimal_value)
                        | Q(added_for_warehouse=search_param.lower() == "true")
                    )
                except ValueError:
                    bundles = bundles.filter(Q(bundle_no__icontains=search_param))

            total_bundles = base_qs.count()
            total_pieces = sum(bundle.pieces for bundle in base_qs)
            total_weight = sum(bundle.weight for bundle in base_qs)

            ready_bundles = base_qs.filter(added_for_warehouse=False)
            ready_bundles_count = ready_bundles.count()
            ready_bundles_pieces = sum(bundle.pieces for bundle in ready_bundles)
            ready_bundles_weight = sum(bundle.weight for bundle in ready_bundles)

            added_bundles = base_qs.filter(added_for_warehouse=True)
            added_bundles_count = added_bundles.count()
            added_bundles_pieces = sum(bundle.pieces for bundle in added_bundles)
            added_bundles_weight = sum(bundle.weight for bundle in added_bundles)

            bundle_list = []
            profile_description = None

            for bundle in bundles:
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
                    item_name = " X ".join(dimension_values)
                else:
                    item_name = "No Dimensions Available"

                profile = die.die_number if die else "No Profile"
                length = detail.length if detail else None
                avg_weight = (
                    float(bundle.weight) / bundle.pieces if bundle.pieces else 0
                )

                if not profile_description:
                    profile_description = item_name

                bundle_list.append(
                    {
                        "id": bundle.id,
                        "bundle_no": bundle.bundle_no,
                        "profile_description": profile_description,
                        "profile": profile,
                        "length": length,
                        "pieces": bundle.pieces,
                        "weight": bundle.weight,
                        "avg_weight": avg_weight,
                        "packing_date_time": bundle.packing_date,
                        "added_for_outword": bundle.added_for_warehouse,
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
                        "total_weight": total_weight,
                        "added_bundles": added_bundles_count,
                        "added_bundles_weight": added_bundles_weight,
                        "added_bundles_pieces": added_bundles_pieces,
                        "ready_bundles": ready_bundles_count,
                        "ready_bundles_weight": ready_bundles_weight,
                        "ready_bundles_pieces": ready_bundles_pieces,
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
    def add_item_by_bundle_ids(self, request, *args, **kwargs):
        """Update added_for_warehouse to True and retrieve bundle details based on bundle IDs from JSON payload"""

        bundle_ids = request.data.get("bundle_id", [])
        outward_id = request.data.get("outward_id", None)

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

        if not outward_id:
            return Response(
                {"success": False, "message": "outward_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        warehouse = Warehouse.objects.filter(id=outward_id).first()
        if not warehouse:
            return Response(
                {"success": False, "message": "Warehouse not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        bundles = BundleInward.objects.filter(pk__in=bundle_ids)

        if not bundles.exists():
            return Response(
                {
                    "success": False,
                    "message": "No bundles found for the given IDs",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bundle_data = []
        with transaction.atomic():
            for bundle in bundles:
                bundle.added_for_warehouse = True
                bundle.save()

                WarehouseBundleOutward.objects.get_or_create(
                    warehouse=warehouse, bundle_inward=bundle
                )

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
                    "added_for_warehouse": bundle.added_for_warehouse,
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
    def restore_item_by_bundle_ids(self, request, *args, **kwargs):
        """Update added_for_warehouse to False and retrieve bundle details based on bundle IDs from JSON payload"""

        bundle_ids = request.data.get("bundle_id", [])
        outward_id = request.data.get("outward_id", None)

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

        if outward_id:
            warehouse = Warehouse.objects.filter(id=outward_id).first()
            if warehouse:
                from warehouse.models import WarehouseBundleOutward

                WarehouseBundleOutward.objects.filter(
                    warehouse=warehouse, bundle_inward_id__in=bundle_ids
                ).delete()

        bundles = BundleInward.objects.filter(pk__in=bundle_ids)

        if not bundles.exists():
            return Response(
                {"success": False, "message": "No bundles found for the given IDs"},
                status=status.HTTP_200_OK,
            )

        bundle_data = []
        for bundle in bundles:
            bundle.added_for_warehouse = False
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
                    "added_for_warehouse": bundle.added_for_warehouse,
                }
            )

        paginator = self.pagination_class()
        paginated_bundles = paginator.paginate_queryset(bundle_data, request)

        return paginator.get_paginated_response(
            {
                "success": True,
                "message": "Restore Item successfully",
                "data": paginated_bundles,
            }
        )

    @action(detail=False, methods=["patch"], url_path="bundle-finalize")
    def warehouse_bundle_finalize(self, request):
        """Finalize bundles for multiple workorder_detail_ids by updating their is_warehouse field to False.
        Only bundles with 'added_for_warehouse=True' and status='Dispatched' are finalized.
        """
        try:
            workorder_detail_ids = request.data.get("workorder_detail_id", [])
            warehouse_outward_id = request.data.get("warehouse_outward_id")

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

            if not warehouse_outward_id:
                return Response(
                    {"success": False, "message": "warehouse_outward_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            warehouse = Warehouse.objects.filter(id=warehouse_outward_id).first()
            if not warehouse:
                return Response(
                    {"success": False, "message": "Warehouse outward not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            outward_bundle_ids = list(
                warehouse.outward_bundles.values_list("id", flat=True)
            )
            logger.info(f"Outward bundle IDs: {outward_bundle_ids}")

            bundles_to_finalize = BundleInward.objects.filter(
                id__in=outward_bundle_ids,
                added_for_warehouse=True,
                status="Warehouse",
                workorder_detail_id__in=workorder_detail_ids,
            )

            logger.info(f"Found {bundles_to_finalize.count()} bundles to finalize")

            if not bundles_to_finalize.exists():
                return Response(
                    {
                        "success": False,
                        "message": "No eligible bundles found to finalize",
                    },
                    status=status.HTTP_200_OK,
                )

            finalized_bundle_ids_list = list(
                bundles_to_finalize.values_list("id", flat=True)
            )

            logger.info(f"Bundle IDs to finalize: {finalized_bundle_ids_list}")

            with transaction.atomic():
                now = timezone.now()

                updated_count = bundles_to_finalize.update(
                    is_warehouse=False,
                    dispatch_date=now,
                    status="Dispatched",
                )
                logger.info(f"Updated {updated_count} bundles: is_warehouse=False")

                warehouse.dispatched = True
                warehouse.approved = True
                warehouse.dispatched_date = now
                warehouse.save()

                logger.info(
                    f"Warehouse {warehouse_outward_id} marked as dispatched and approved"
                )

                for bundle_id in finalized_bundle_ids_list:
                    bundle = BundleInward.objects.filter(id=bundle_id).first()
                    if bundle:
                        obj, created = WarehouseBundleInward.objects.get_or_create(
                            warehouse=warehouse, bundle_inward=bundle
                        )
                        if created:
                            logger.info(
                                f"Created WarehouseBundleInward for bundle {bundle_id}"
                            )
                        else:
                            logger.info(
                                f"WarehouseBundleInward already exists for bundle {bundle_id}"
                            )

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="FINALIZE BUNDLE",
                module_name="Warehouse BundleOutward",
                description=f"Finalized WareHouse bundles: {finalized_bundle_ids_list}",
                request=request,
                payload=payload,
            )

            return Response(
                {
                    "success": True,
                    "message": f"{updated_count} bundle(s) finalized successfully for warehouse",
                    "finalized_bundles_count": updated_count,
                    "finalized_bundle_ids": finalized_bundle_ids_list,
                    "approved": warehouse.approved,
                    "dispatched": warehouse.dispatched,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception(f"Error finalizing warehouse bundles: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"An error occurred while finalizing warehouse bundles: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="packing-slip-summary")
    def packing_slip_summary(self, request):
        outward_id = request.query_params.get("outward_id")
        if not outward_id:
            return Response(
                {"status": False, "message": "outward_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            warehouse = Warehouse.objects.get(id=outward_id)
        except Warehouse.DoesNotExist:
            return Response(
                {"status": False, "message": "Warehouse record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        workorder = warehouse.workorder
        workorder_details = WorkOrderDetail.objects.filter(workorder=workorder).exclude(
            status="Pending"
        )

        bundle_ids = list(warehouse.outward_bundles.values_list("id", flat=True))

        summary = []
        total_net_weight = 0
        total_gross_weight = 0
        total_pieces = 0
        total_bundles = 0

        for detail in workorder_details:
            dispatched_bundles = BundleInward.objects.filter(
                workorder_detail=detail,
                added_for_warehouse=True,
                id__in=bundle_ids,
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
                        str(die.dimension1),
                        str(die.dimension2) if die.dimension2 else "",
                        str(die.dimension3) if die.dimension3 else "",
                        str(die.dimension4) if die.dimension4 else "",
                    ],
                )
            )

            alloy_code = detail.alloy.alloy_code if detail.alloy else ""
            temper_name = detail.temper.temper_code_new if detail.temper else ""
            alloy_temper = f"{alloy_code} - {temper_name}".strip(" -")

            net_wt = aggregates["total_net_weight"] or 0
            gross_wt = aggregates["total_gross_weight"] or 0

            summary.append(
                {
                    "alloy & temper": alloy_temper,
                    "length": detail.length,
                    "die_number": die.die_number if die else None,
                    "die_diagram": die.die_diagram if die else None,
                    "die_dimensions": die_dimensions,
                    "total_net_weight": f"{net_wt: .3f}",
                    "total_gross_weight": f"{gross_wt: .3f}",
                    "total_pieces": aggregates["total_pieces"] or 0,
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

        vehicle_details = {
            "vehicle_id": warehouse.vehicle_no_id if warehouse.vehicle_no else None,
            "vehicle_no": (
                warehouse.vehicle_no.vehicle_no if warehouse.vehicle_no else None
            ),
            "transporter_name": (
                warehouse.vehicle_no.party_name.party_name
                if warehouse.vehicle_no and warehouse.vehicle_no.party_name
                else None
            ),
        }

        response_data = {
            "order_no": workorder.order_no,
            "dispatched_date": warehouse.dispatched_date,
            "customer_name": customer.customer_name if customer else None,
            "phone_number": customer.phone_number if customer else None,
            "office_address": office_address,
            "factory_address": factory_address,
            "vehicle_details": vehicle_details,
            "slip_no": warehouse.slip_no,
            "remarks": warehouse.remarks,
            "summary": summary,
            "total_summary": {
                "total_net_weight": f"{total_net_weight: .3f}",
                "total_gross_weight": f"{total_gross_weight: .3f}",
                "total_pieces": total_pieces,
                "total_bundles": total_bundles,
            },
        }

        return Response(
            {"status": True, "data": response_data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="packing-slip-bundles")
    def get_warehouse_packing_slip_bundles(self, request):
        outward_id = request.query_params.get("outward_id")
        if not outward_id:
            return Response(
                {"success": False, "message": "outward_id is required"}, status=400
            )

        try:
            warehouse = Warehouse.objects.select_related("workorder").get(id=outward_id)
        except Warehouse.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid outward_id"}, status=404
            )

        workorder = warehouse.workorder
        workorder_details = WorkOrderDetail.objects.filter(workorder=workorder)

        bundle_ids = list(warehouse.outward_bundles.values_list("id", flat=True))

        grouped_bundles = {}
        total_pieces = 0
        total_net_weight = 0.0
        total_gross_weight = 0.0

        for detail in workorder_details:
            bundles = BundleInward.objects.filter(
                workorder_detail=detail, added_for_warehouse=True, id__in=bundle_ids
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
                            str(die.dimension1 or ""),
                            str(die.dimension2 or ""),
                            str(die.dimension3 or ""),
                            str(die.dimension4 or ""),
                        ],
                    )
                )

                data = {
                    "type": "data",
                    "bundle_no": bundle.bundle_no,
                    "die_number": die.die_number,
                    "die_diagram": die.die_diagram,
                    "die_dimensions": die_dimensions,
                    "length": length,
                    "pieces": bundle.pieces or 0,
                    "net_weight": float(bundle.weight or 0),
                    "gross_weight": float(bundle.gross_weight or 0),
                    "dispatch_date": bundle.dispatch_date,
                }

                grouped_bundles.setdefault(group_key, []).append(data)

        final_bundle_list = []

        for (section, length), bundle_group in grouped_bundles.items():
            group_pieces = 0
            group_net = 0.0
            group_gross = 0.0
            bundle_count = len(bundle_group)

            for bundle in bundle_group:
                final_bundle_list.append(bundle)
                group_pieces += bundle["pieces"]
                group_net += bundle["net_weight"]
                group_gross += bundle["gross_weight"]

                total_pieces += bundle["pieces"]
                total_net_weight += bundle["net_weight"]
                total_gross_weight += bundle["gross_weight"]

                bundle["net_weight"] = f"{bundle['net_weight']:.3f}"
                bundle["gross_weight"] = f"{bundle['gross_weight']:.3f}"

            final_bundle_list.append(
                {
                    "type": "subtotal",
                    "description": f"{len(bundle_group)} Bundles",
                    "pieces": group_pieces,
                    "net_weight_kg": f"{group_net:.3f}",
                    "gross_weight_kg": f"{group_gross:.3f}",
                }
            )

        total_data_count = sum(len(group) for group in grouped_bundles.values())

        customer = workorder.bill_to
        office_address = ", ".join(
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

        factory_address = ", ".join(
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

        vehicle_details = {
            "vehicle_id": warehouse.vehicle_no_id if warehouse.vehicle_no else None,
            "vehicle_no": (
                warehouse.vehicle_no.vehicle_no if warehouse.vehicle_no else None
            ),
            "transporter_name": (
                warehouse.vehicle_no.party_name.party_name
                if warehouse.vehicle_no and warehouse.vehicle_no.party_name
                else None
            ),
        }

        response = {
            "success": True,
            "data": {
                "order_no": workorder.order_no,
                "dispatched_date": warehouse.dispatched_date,
                "vehicle_details": vehicle_details,
                "slip_no": warehouse.slip_no,
                "remarks": warehouse.remarks,
                "customer_name": customer.customer_name,
                "phone_number": customer.phone_number,
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
