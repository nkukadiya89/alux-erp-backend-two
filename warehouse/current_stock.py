import logging
from operator import itemgetter

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from requests import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from bundle_inward.models import BundleInward
from bundle_outward.models import BundleOutward
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from customer.models import Customer
from utils.pagination import Pagination
from workorder.models import WorkOrder, WorkOrderDetail

logger = logging.getLogger("file")


class WarehouseCurrentStockViewSet(BaseModelViewSet, ArchiveMixin):
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=["get"], url_path="party-wise-stock-summery")
    def party_wise_stock_summery(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").strip()
            ordering = request.query_params.get("ordering", "customer_name").strip()

            base_qs = (
                BundleInward.objects.filter(
                    status="Warehouse",
                    is_warehouse=True,
                    added_for_warehouse=False,
                    deleted=False,
                )
                .select_related("workorder__bill_to")
                .filter(workorder__status__in=["Open", "Warehouse", "Dispatched"])
            )

            total_weight_sum = float(base_qs.aggregate(w=Sum("weight"))["w"] or 0.0)
            total_bundeles = base_qs.aggregate(c=Count("id"))["c"] or 0
            verified_weight = float(
                base_qs.filter(verified=True).aggregate(w=Sum("weight"))["w"] or 0.0
            )
            unverified_weight = float(
                base_qs.filter(verified=False).aggregate(w=Sum("weight"))["w"] or 0.0
            )

            grouped = base_qs.values(
                "workorder__bill_to_id", "workorder__bill_to__customer_name"
            ).annotate(total_weight=Sum("weight"))

            customer_data = []
            for item in grouped:
                customer_id = item["workorder__bill_to_id"]
                customer_name = item["workorder__bill_to__customer_name"] or "Unknown"
                weight = float(item["total_weight"] or 0.0)
                if weight > 0:
                    customer_data.append(
                        {
                            "id": customer_id,
                            "customer_name": customer_name,
                            "packed_weight": round(weight, 3),
                        }
                    )

            if search_query:
                customer_data = [
                    c
                    for c in customer_data
                    if search_query.lower() in c["customer_name"].lower()
                ]

            reverse = ordering.startswith("-")
            order_key = ordering.lstrip("-")
            if order_key in ["customer_name", "packed_weight"]:
                customer_data = sorted(
                    customer_data, key=itemgetter(order_key), reverse=reverse
                )

            page = self.paginate_queryset(customer_data)
            if page is not None:
                counts = {
                    "total_kg": f"{total_weight_sum:,.3f} Kg",
                    "total_bundles": total_bundeles,
                    "verified": f"{verified_weight:,.3f} Kg",
                    "un_verified": f"{unverified_weight:,.3f} Kg",
                }
                return self.get_paginated_response(
                    {
                        "success": True,
                        "data": {"counts": counts, "customer_details": page},
                    }
                )

            counts = {
                "total_kg": f"{total_weight_sum:,.3f} Kg",
                "total_bundeles": total_bundeles,
                "verified": f"{verified_weight:,.3f} Kg",
                "un_verified": f"{unverified_weight:,.3f} Kg",
            }

            return Response(
                {
                    "success": True,
                    "data": {"counts": counts, "customer_details": customer_data},
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="workorders/(?P<customer_id>\\d+)")
    def get_workorders(self, request, customer_id, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "-id")
            reverse = False

            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            work_orders = (
                WorkOrder.objects.filter(bill_to_id=customer_id, deleted=0)
                .filter(
                    status__in=["Open", "Warehouse", "Dispatched"]
                )  
                .order_by("-id")
            )
            customer = Customer.objects.filter(id=customer_id).first()
            customer_name = customer.customer_name if customer else "Unknown Customer"

            response_data = []
            bundle_data_ids = []
            for work_order in work_orders:
                order_details = WorkOrderDetail.objects.filter(workorder=work_order)

                for detail in order_details:
                    bundles = BundleInward.objects.filter(
                        status="Warehouse",
                        workorder_detail=detail,
                        is_warehouse=True,
                        added_for_warehouse=False,
                        deleted=False,
                    )
                    bundle_data_ids.extend(bundles.values_list("id", flat=True))
                    if not bundles.exists():
                        continue 

                    aggregated = bundles.aggregate(
                        packed_wt_kg=Sum("weight"), packed_pcs=Sum("pieces")
                    )

                    packed_wt_kg = float(aggregated["packed_wt_kg"] or 0)
                    packed_pcs = aggregated["packed_pcs"] or 0

                    if round(packed_wt_kg, 3) and packed_pcs == 0:
                        continue

                    die = detail.die_profile
                    if die:
                        dimensions = [
                            die.dimension1,
                            die.dimension2,
                            die.dimension3,
                            die.dimension4,
                        ]
                        item_name = " X ".join(
                            [f"{dim} MM" for dim in dimensions if dim]
                        )
                    else:
                        item_name = "No Dimensions Available"

                    data = {
                        "customer_name": customer_name,
                        "work_order_no": work_order.order_no,
                        "section": die.die_number if die else None,
                        "die_diagram": (
                            die.die_diagram if die and die.die_diagram else None
                        ),
                        "length_mm": float(detail.length) if detail.length else 0,
                        "item_name": item_name,
                        "order_kg": f"{(detail.net_weight or 0):.3f}",
                        "order_pcs": detail.pieces or 0,
                        "packed_wt_kg": f"{(packed_wt_kg or 0):.3f}",
                        "packed_pcs": packed_pcs,
                    }

                    if search_query and not any(
                        search_query in str(value).lower() for value in data.values()
                    ):
                        continue

                    response_data.append(data)
            try:
                response_data = sorted(
                    response_data, key=itemgetter(ordering), reverse=reverse
                )
            except KeyError:
                pass  

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(response_data, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "message": "Work orders retrieved successfully",
                    "data": paginated_data,
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=500,
            )

    @action(
        detail=False,
        methods=["get"],
        url_path="warehouse-packed-bundles/(?P<customer_id>\\d+)",
    )
    def get_warehouse_packed_bundles(self, request, customer_id, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get(
                "ordering", "bundle_no"
            ) 
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            work_orders = WorkOrder.objects.filter(
                bill_to_id=customer_id,
                deleted=False,
                status__in=["Open", "Warehouse", "Dispatched"],
            ).order_by("-id")
            work_order_ids = work_orders.values_list("id", flat=True)

            bundles = BundleInward.objects.filter(
                workorder_id__in=work_order_ids,
                status="Warehouse",
                is_warehouse=True,
                added_for_warehouse=False,
                deleted=False,
            ).order_by("-id")

            customer = Customer.objects.filter(id=customer_id).first()
            customer_name = customer.customer_name if customer else "Unknown Customer"

            response_data = []

            for bundle in bundles:
                try:
                    detail = bundle.workorder_detail  
                    die = (
                        detail.die_profile if detail else None
                    ) 

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

                    row = {
                        "bundle_no": bundle.bundle_no,
                        "section": die.die_number if die else None,
                        "length_mm": (
                            float(detail.length) if detail and detail.length else 0
                        ),
                        "item_name": item_name,
                        "pieces": bundle.pieces,
                        "weight_kg": f"{bundle.weight:.3f}",
                        "avg_weight_kg": (
                            f"{(float(bundle.gross_weight) / bundle.pieces):.3f}"
                            if bundle.pieces
                            else "0.000"
                        ),
                        "packing_date": bundle.packing_date,
                        "workorder_no": detail.workorder.order_no,
                    }

                    if search_query:
                        if not any(
                            search_query in str(value).lower() for value in row.values()
                        ):
                            continue

                    response_data.append(row)

                except Exception as e:
                    print(f"Error processing bundle {bundle.bundle_no}: {e}")

            try:
                response_data = sorted(
                    response_data, key=itemgetter(ordering), reverse=reverse
                )
            except KeyError:
                pass 

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(response_data, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "customer_name": customer_name,
                    "data": paginated_data,
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=500,
            )

    @action(detail=False, methods=["get"], url_path="all-dispatched-bundles")
    def get_all_dispatched_bundles(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "bundle_no")
            reverse = ordering.startswith("-")
            ordering_field = ordering.lstrip("-")

            bundles = (
                BundleInward.objects.filter(
                    status="Warehouse",
                    is_warehouse=True,
                    deleted=False,
                    added_for_warehouse=False,
                    workorder_detail__isnull=False,
                )
                .select_related("workorder__bill_to", "workorder_detail__die_profile")
                .filter(workorder__status__in=["Open", "Warehouse", "Dispatched"])
                .order_by("-id")
            )

            counts = {
                "total_kg": f'{round(bundles.aggregate(w=Sum("weight"))["w"] or 0.0, 3)} Kg',
                "verified_bundles": bundles.filter(verified=True).aggregate(c=Count("id"))["c"] or 0,
                "un_verified_bundles": bundles.filter(verified=False).aggregate(c=Count("id"))["c"] or 0,
                "total_bundles": bundles.aggregate(c=Count("id"))["c"] or 0,
                "verified_kg": f'{round(bundles.filter(verified=True).aggregate(w=Sum("weight"))["w"] or 0.0, 3)} Kg',
                "un_verified_kg": f'{round(bundles.filter(verified=False).aggregate(w=Sum("weight"))["w"] or 0.0, 3)} Kg',
            }

            response_data = []
            for bundle in bundles:
                detail = bundle.workorder_detail
                die = detail.die_profile if detail else None

                item_name = (
                    " X ".join(
                        [
                            f"{dim} MM"
                            for dim in [
                                die.dimension1,
                                die.dimension2,
                                die.dimension3,
                                die.dimension4,
                            ]
                            if dim
                        ]
                    )
                    if die
                    else "No Dimensions Available"
                )

                customer = bundle.workorder.bill_to if bundle.workorder else None
                customer_name = (
                    customer.customer_name if customer else "Unknown Customer"
                )

                row = {
                    "bundle_id": bundle.id,
                    "bundle_no": bundle.bundle_no,
                    "profile": die.die_number if die else "No Die Profile",
                    "length_mm": detail.length if detail else 0,
                    "profile_description": item_name,
                    "pieces": bundle.pieces,
                    "weight_kg": f"{bundle.weight:.3f}" if bundle.weight else 0,
                    "avg_weight_kg": (
                        float(bundle.weight) / bundle.pieces if bundle.pieces else 0
                    ),
                    "packing_date": bundle.packing_date,
                    "customer_name": customer_name,
                }

                if search_query:
                    if not any(
                        search_query in str(value).lower() for value in row.values()
                    ):
                        continue

                response_data.append(row)

            try:
                response_data = sorted(
                    response_data, key=itemgetter(ordering_field), reverse=reverse
                )
            except KeyError:
                pass  

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(response_data, request)

            return paginator.get_paginated_response(
                {
                    "success": True,
                    "message": "Dispatched bundles retrieved successfully",
                    "data": {
                        "counts": counts,
                        "bundles": paginated_data,
                    },
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=500,
            )


    @action(detail=False, methods=["get"], url_path="warehouse-item-wise-stock-summary")
    def warehouse_item_wise_stock_summary(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "profile")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            base_bundles = (
                BundleInward.objects.filter(
                    status="Warehouse",
                    is_warehouse=True,
                    deleted=False,
                    added_for_warehouse=False,
                    workorder_detail__isnull=False,
                )
                .filter(workorder__status__in=["Warehouse", "Open", "Dispatched"])
                .exclude(workorder__status="Closed")
            )

            bundles = (
                base_bundles.select_related(
                    "workorder_detail__die_profile",
                    "workorder__bill_to",
                    "workorder_detail__alloy"
                )
                .values(
                    "workorder_detail_id",
                    "workorder__bill_to__customer_name",
                    "workorder_detail__die_profile__die_number",
                    "workorder_detail__length",
                    "workorder_detail__net_weight",
                    "workorder_detail__pieces",
                    "workorder__order_no",
                    "workorder_detail__alloy_id",        
                    "workorder_detail__alloy__alloy_code",
                    "workorder_detail__alloy__color_code",
                    "workorder_detail__temper__temper_code_new",
                    "workorder_detail__alloy__standard__name",
                    "workorder_detail__temper__standard__name"
                )

                .annotate(
                    total_weight=Sum("weight"),
                    total_pieces=Sum("pieces"),
                    total_bundles=Count("id"),  
                )
            )

            if search_query:
                bundles = bundles.filter(
                    Q(workorder__bill_to__customer_name__icontains=search_query)
                    | Q(
                        workorder_detail__die_profile__die_number__icontains=search_query
                    )
                )

            if ordering in ["profile", "customer_name", "total_weight"]:
                if ordering == "profile":
                    ordering = "workorder_detail__die_profile__die_number"
                bundles = bundles.order_by(
                    F(ordering).desc() if reverse else F(ordering)
                )

            paginator = self.pagination_class()
            paginated_bundles = paginator.paginate_queryset(bundles, request)

            summary_list = []
            for bundle in paginated_bundles:
                die_number = bundle["workorder_detail__die_profile__die_number"]
                customer_name = bundle["workorder__bill_to__customer_name"]
                order_no = bundle["workorder__order_no"]
                alloy_name = bundle[
                    "workorder_detail__alloy__alloy_code"
                ]
                temper_code = bundle[
                    "workorder_detail__temper__temper_code_new"
                ]
                alloy_standard = bundle[
                    "workorder_detail__alloy__standard__name"
                ]
                temper_standard = bundle[
                    "workorder_detail__temper__standard__name"
                ]

                row = {
                    "workorder_no": order_no,
                    "profile": die_number,
                    "length": bundle["workorder_detail__length"],
                    "customer_name": customer_name,
                    "alloy": (
                        f"{alloy_name} ({alloy_standard}) / {temper_code} ({temper_standard})"
                        if alloy_name or temper_code or alloy_standard or temper_standard
                        else None
                    ),
                    "total_weight": f"{bundle['total_weight']:.3f}",
                    "total_pieces": bundle["total_pieces"],
                    "total_bundles": bundle["total_bundles"],
                }
                summary_list.append(row)

            counts = {
                "total_kg": f'{round(base_bundles.aggregate(Sum("weight"))["weight__sum"] or 0.0, 3)} Kg',
                "verified_kg": f'{round(base_bundles.filter(verified=True).aggregate(Sum("weight"))["weight__sum"] or 0.0, 3)} Kg',
                "un_verified_kg": f'{round(base_bundles.filter(verified=False).aggregate(Sum("weight"))["weight__sum"] or 0.0, 3)} Kg',
                "total_bundles": base_bundles.aggregate(Count("id"))["id__count"] or 0,
                "verified_bundles": base_bundles.filter(verified=True).aggregate(Count("id"))["id__count"] or 0,
                "un_verified_bundles": base_bundles.filter(verified=False).aggregate(Count("id"))["id__count"] or 0,

            }

            return paginator.get_paginated_response(
                {"success": True, "data": {"counts": counts, "summary": summary_list}}
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
