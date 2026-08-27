import logging
from operator import itemgetter

from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from bundle_inward.models import BundleInward
from common.master_views import BaseModelViewSet
from customer.models import Customer
from utils.pagination import Pagination
from workorder.models import WorkOrder, WorkOrderDetail
from workorder.serializers import WorkOrderSerializers

logger = logging.getLogger("file")


class CurrentStockViewSet(BaseModelViewSet):
    queryset = (
         WorkOrder.objects.filter(deleted=False)
        .select_related("bill_to", "created_by", "updated_by", "deleted_by")
        .order_by("-id")
    )

    serializer_class = WorkOrderSerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=["get"], url_path="party-wise-stock-summery")
    def party_wise_stock_summery(self, request, *args, **kwargs):
        search_query = request.query_params.get("search", "").strip()
        ordering = request.query_params.get("ordering", "").strip()

        customers = Customer.objects.all()
        if search_query:
            customers = customers.filter(Q(customer_name__icontains=search_query))

        total_bundles = BundleInward.objects.filter(
            status="Packed",
            deleted=False,
            added_for_outword=False,
            is_excess_stock=False,
        )
        verified_bundles = total_bundles.filter(verified=True)
        un_verified_bundles = total_bundles.filter(verified=False)

        counts = {
            "total_kg": f'{round(total_bundles.aggregate(w=Sum("weight"))["w"] or 0.0, 3)} Kg',
            "verified_kg": f'{round(verified_bundles.aggregate(w=Sum("weight"))["w"] or 0.0, 3)} Kg',
            "un_verified_kg": f'{round(un_verified_bundles.aggregate(w=Sum("weight"))["w"] or 0.0, 3)} Kg',
            "total_bundles": total_bundles.count(),
            "verified_bundles": verified_bundles.count(),
            "un_verified_bundles": un_verified_bundles.count(),  
        }

        customer_data = []
        for customer in customers:
            total_weight = (
                BundleInward.objects.filter(
                    workorder__bill_to=customer,
                    status="Packed",
                    is_excess_stock=False,
                    added_for_outword=False,
                    deleted=False,
                ).aggregate(total_weight=Sum("weight"))["total_weight"]
                or 0.0
            )
            if round(total_weight, 3) > 0:
                customer_data.append(
                    {
                        "id": customer.id,
                        "customer_name": customer.customer_name,
                        "packed_weight": f"{total_weight:.3f}",
                    }
                )

        if ordering:
            reverse = ordering.startswith("-")
            key = ordering.lstrip("-")
            if key in ["customer_name", "packed_weight"]:
                customer_data.sort(key=itemgetter(key), reverse=reverse)
        else:
            customer_data.sort(key=itemgetter("customer_name"))

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(customer_data, request)

        return paginator.get_paginated_response(
            {
                "success": True,
                "data": {
                    "counts": counts,
                    "customer_details": paginated_data,
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="excess-stock-summery")
    def excess_stock_summery(self, request, *args, **kwargs):
        excess_bundles = BundleInward.objects.filter(
            status="Packed",
            deleted=False,
            added_for_outword=False,
            is_excess_stock=True,
        )

        total_weight = excess_bundles.aggregate(total=Sum("weight"))["total"] or 0.0

        verified_weight = (
            excess_bundles.filter(verified=True).aggregate(w=Sum("weight"))["w"] or 0.0
        )

        un_verified_weight = (
            excess_bundles.filter(verified=False).aggregate(w=Sum("weight"))["w"] or 0.0
        )

        total_count = excess_bundles.aggregate(cnt=Count("id"))["cnt"] or 0
        verified_count = (
            excess_bundles.filter(verified=True).aggregate(cnt=Count("id"))["cnt"] or 0
        )
        unverified_count = (
            excess_bundles.filter(verified=False).aggregate(cnt=Count("id"))["cnt"] or 0
        )

        total_weight_str = f"{total_weight:.3f}"
        verified_weight_str = f"{verified_weight:.3f}"
        un_verified_weight_str = f"{un_verified_weight:.3f}"

        counts = {
            "total_kg": f"{total_weight_str} Kg ({total_count} bundles)",
            "verified_kg": f"{verified_weight_str} Kg ({verified_count} bundles)",
            "un_verified_kg": f"{un_verified_weight_str} Kg ({unverified_count} bundles)",
            "total_bundles": f"{total_count} Bundles",
            "verified_bundles": f"{verified_count} Bundles",
            "un_verified_bundles": f"{unverified_count} Bundles",
        }

        return Response(
            {
                "success": True,
                "data": {
                    "customer_name": "Excess Stock",
                    "packed_weight": total_weight_str,  # String with 3 decimals
                    "counts": counts,
                },
            },
            status=200,
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

            work_orders = WorkOrder.objects.filter(
                bill_to_id=customer_id, deleted=False
            ).order_by("-id")
            customer = Customer.objects.filter(id=customer_id).first()
            customer_name = customer.customer_name if customer else "Unknown Customer"

            response_data = []

            for work_order in work_orders:
                order_details = WorkOrderDetail.objects.filter(
                    workorder=work_order, packed_weight__gt=0
                )
                for detail in order_details:

                    bundles = BundleInward.objects.filter(
                        workorder_detail=detail,
                        status="Packed",
                        deleted=False,
                        is_excess_stock=False,
                        added_for_outword=False,
                    )

                    packed_wt_kg = (
                        bundles.aggregate(total_weight=Sum("weight"))["total_weight"]
                        or 0
                    )
                    packed_pcs = (
                        bundles.aggregate(total_pcs=Sum("pieces"))["total_pcs"] or 0
                    )

                    if round(packed_wt_kg, 3) == 0 and packed_pcs == 0:
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
                        "section": (
                            detail.die_profile.die_number
                            if detail.die_profile
                            else None
                        ),
                        "die_diagram": (
                            detail.die_profile.die_diagram
                            if detail.die_profile and detail.die_profile.die_diagram
                            else None
                        ),
                        "length_mm": float(detail.length) if detail.length else 0,
                        "item_name": item_name,
                        "order_kg": (
                            float(detail.net_weight) if detail.net_weight else 0
                        ),
                        "order_pcs": detail.pieces if detail.pieces else 0,
                        "packed_wt_kg": packed_wt_kg,
                        "packed_pcs": packed_pcs,
                    }

                    if search_query:
                        if not any(
                            search_query in str(value).lower()
                            for value in data.values()
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
        detail=False, methods=["get"], url_path="packed-bundles/(?P<customer_id>\\d+)"
    )
    def get_packed_bundles(self, request, customer_id, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "bundle_no")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            work_orders = WorkOrder.objects.filter(
                bill_to_id=customer_id, deleted=False
            ).order_by("-id")
            work_order_ids = work_orders.values_list("id", flat=True)

            bundles = BundleInward.objects.filter(
                workorder_id__in=work_order_ids,
                status="Packed",
                is_excess_stock=False,
                added_for_outword=False,
                deleted=False,
            ).order_by("-id")

            customer = Customer.objects.filter(id=customer_id).first()
            customer_name = customer.customer_name if customer else "Unknown Customer"

            response_data = []
            total_pieces = 0
            total_weight = 0

            for bundle in bundles:
                try:
                    detail = bundle.workorder_detail
                    die = detail.die_profile if detail else None

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

                    row = {
                        "bundle_no": bundle.bundle_no,
                        "section": die.die_number if die else None,
                        "length_mm": (
                            float(detail.length) if detail and detail.length else 0
                        ),
                        "item_name": item_name,
                        "pieces": bundle.pieces,
                        "weight_kg": float(bundle.weight) if bundle.weight else 0,
                        "avg_weight_kg": (
                            round(float(bundle.gross_weight) / bundle.pieces, 3)
                            if bundle.pieces
                            else 0
                        ),
                        "workorder_no": (bundle.workorder.order_no),
                        "packing_date": bundle.packing_date,
                    }

                    if search_query:
                        if not any(
                            search_query in str(value).lower() for value in row.values()
                        ):
                            continue

                    total_pieces += row["pieces"]
                    total_weight += row["weight_kg"]

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
                    "total_pieces": total_pieces,
                    "total_weight_kg": round(total_weight, 3),
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=500,
            )

    @action(detail=False, methods=["get"], url_path="all-packed-bundles")
    def get_all_packed_bundles(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "bundle_no")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            bundles = (
                BundleInward.objects.filter(
                    status="Packed",
                    # is_excess_stock=False,
                    deleted=False,
                    added_for_outword=False,
                )
                .select_related("workorder__bill_to", "workorder_detail__die_profile")
                .order_by("-id")
            )

            total_kg = round(bundles.aggregate(w=Sum("weight"))["w"] or 0.0, 3)
            verified_kg = round(
                bundles.filter(verified=True).aggregate(w=Sum("weight"))["w"] or 0.0, 3
            )
            un_verified_kg = round(
                bundles.filter(verified=False).aggregate(w=Sum("weight"))["w"] or 0.0, 3
            )
            total_bundles = bundles.count()
            verified_bundles = bundles.filter(verified=True).count()
            un_verified_bundles = bundles.filter(verified=False).count()

            response_data = [
                {
                    "bundle_id": bundle.id,
                    "bundle_no": bundle.bundle_no,
                    "profile": (
                        getattr(
                            bundle.workorder_detail.die_profile,
                            "die_number",
                            "No Die Profile",
                        )
                        if bundle.workorder_detail
                        and bundle.workorder_detail.die_profile
                        else "No Die Profile"
                    ),
                    "length_mm": (
                        getattr(bundle.workorder_detail, "length", 0)
                        if bundle.workorder_detail
                        else 0
                    ),
                    "profile_description": (
                        " X ".join(
                            [
                                f"{dim} MM"
                                for dim in [
                                    getattr(
                                        bundle.workorder_detail.die_profile,
                                        "dimension1",
                                        None,
                                    ),
                                    getattr(
                                        bundle.workorder_detail.die_profile,
                                        "dimension2",
                                        None,
                                    ),
                                    getattr(
                                        bundle.workorder_detail.die_profile,
                                        "dimension3",
                                        None,
                                    ),
                                    getattr(
                                        bundle.workorder_detail.die_profile,
                                        "dimension4",
                                        None,
                                    ),
                                ]
                                if dim
                            ]
                        )
                        if bundle.workorder_detail
                        and bundle.workorder_detail.die_profile
                        else "No Dimensions Available"
                    ),
                    "pieces": bundle.pieces,
                    "weight_kg": float(bundle.weight) if bundle.weight else 0,
                    "avg_weight_kg": (
                        float(bundle.weight) / bundle.pieces if bundle.pieces else 0
                    ),
                    "packing_date": bundle.packing_date,
                    "customer_name": (
                        getattr(
                            bundle.workorder.bill_to,
                            "customer_name",
                            "Unknown Customer",
                        )
                        if bundle.workorder and bundle.workorder.bill_to
                        else "Unknown Customer"
                    ),
                }
                for bundle in bundles
            ]

            if search_query:
                response_data = [
                    row
                    for row in response_data
                    if any(search_query in str(value).lower() for value in row.values())
                ]

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
                    "message": "Packed bundles retrieved successfully",
                    "data": {
                        "counts": {
                            "total_kg": f"{total_kg} Kg",
                            "verified_kg": f"{verified_kg} Kg",
                            "un_verified_kg": f"{un_verified_kg} Kg",
                            "total_bundles": total_bundles,
                            "verified_bundles": verified_bundles,
                            "un_verified_bundles": un_verified_bundles,
                        },
                        "bundles": paginated_data,
                    },
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"An error occurred: {str(e)}"},
                status=500,
            )

    @action(detail=False, methods=["get"], url_path="item-wise-stock-summary")
    def item_wise_stock_summary(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get("search", "").lower()
            ordering = request.query_params.get("ordering", "profile")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            total_bundles_qs = BundleInward.objects.filter(
                status="Packed",
                is_excess_stock=False,
                deleted=False,
                added_for_outword=False,
            ).select_related(
                "workorder_detail__die_profile",
                "workorder_detail__workorder__bill_to",
                "workorder_detail__alloy",
            )
            total_weight = round(
                total_bundles_qs.aggregate(w=Sum("weight"))["w"] or 0.0, 3
            )
            verified_kg = round(
                total_bundles_qs.filter(verified=True).aggregate(w=Sum("weight"))["w"]
                or 0.0,
                3,
            )
            un_verified_kg = round(
                total_bundles_qs.filter(verified=False).aggregate(w=Sum("weight"))["w"]
                or 0.0,
                3,
            )

            total_bundles = total_bundles_qs.count()
            verified_bundles = total_bundles_qs.filter(verified=True).count()
            un_verified_bundles = total_bundles_qs.filter(verified=False).count()


            counts = {
                "total_kg": f"{total_weight} Kg",
                "verified_kg": f"{verified_kg} Kg",
                "un_verified_kg": f"{un_verified_kg} Kg",
                "total_bundles": total_bundles,
                "verified_bundles": verified_bundles,
                "un_verified_bundles": un_verified_bundles,
            }

            from collections import defaultdict

            detail_bundles = defaultdict(list)
            for bundle in total_bundles_qs:
                if bundle.workorder_detail_id:
                    detail_bundles[bundle.workorder_detail_id].append(bundle)

            detail_ids = list(detail_bundles.keys())
            details = WorkOrderDetail.objects.filter(id__in=detail_ids).select_related(
                "die_profile", "workorder__bill_to", "alloy"
            )
            details_map = {d.id: d for d in details}

            summary_list = []
            for detail_id, bundles in detail_bundles.items():
                detail = details_map.get(detail_id)
                if not detail:
                    continue

                die_number = (
                    detail.die_profile.die_number if detail.die_profile else None
                )
                customer_name = (
                    detail.workorder.bill_to.customer_name
                    if detail.workorder and detail.workorder.bill_to
                    else None
                )
                order_no = detail.workorder.order_no if detail.workorder else None
                alloy_name = detail.alloy.alloy_code if detail.alloy else None
                alloy_standard = detail.alloy.standard.name if detail.alloy.standard else None
                temper_code = detail.temper.temper_code_new if detail.temper else None
                temper_standard = detail.temper.standard.name if detail.temper.standard else None

                row = {
                    "workorder_no": order_no,
                    "profile": die_number,
                    "length": detail.length,
                    "customer_name": customer_name,
                    "alloy": (
                        f"{alloy_name} ({alloy_standard}) / {temper_code} ({temper_standard})"
                        if alloy_name or temper_code or alloy_standard or temper_standard
                        else None
                    ),
                    "total_weight": f"{detail.net_weight:.3f}",
                    "total_pieces": detail.pieces,
                    "total_bundles": len(bundles),
                }

                if search_query:
                    if not any(
                        search_query in str(value).lower()
                        for value in row.values()
                        if value
                    ):
                        continue

                summary_list.append(row)
            try:
                summary_list = sorted(
                    summary_list, key=itemgetter(ordering), reverse=reverse
                )
            except KeyError:
                pass

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(summary_list, request)

            return paginator.get_paginated_response(
                {"success": True, "data": {"counts": counts, "summary": paginated_data}}
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
