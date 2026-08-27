from datetime import date, datetime, timedelta

from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bundle_inward.models import BundleInward, ExcessStock
from die.models import Die, DieTool
from planning.models import Planning
from production.models import Production
from inquiry.models import Inquiry
from quotation.models import Quotation
from warehouse.models import Warehouse
from workorder.models import WorkOrder, WorkOrderDetail


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        # --- Validation ---
        if month and not year:
            return Response(
                {
                    "success": False,
                    "message": "Year is required when month is provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Date Range Logic ---
        if start_date and end_date:
            try:
                start_date = timezone.make_aware(
                    datetime.strptime(start_date, "%d-%m-%Y")
                )
                end_date = timezone.make_aware(
                    datetime.strptime(end_date, "%d-%m-%Y")
                ) + timedelta(days=1)
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid date format. Use DD-MM-YYYY",
                    },
                    status=400,
                )

        elif month and year:
            try:
                month = int(month)
                year = int(year)
                start_date = make_aware(datetime(year, month, 1))
                end_date = make_aware(
                    datetime(year + (1 if month == 12 else 0), (month % 12) + 1, 1)
                )
            except ValueError:
                return Response(
                    {"success": False, "message": "Invalid month or year format."},
                    status=400,
                )

        elif year:
            try:
                year = int(year)
                start_date = datetime(year, 1, 1)
                end_date = datetime(year + 1, 1, 1)
            except ValueError:
                return Response(
                    {"success": False, "message": "Invalid year format."}, status=400
                )
        else:
            today = timezone.now()
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1)

        # --- Query ---
        dies_in_range = Die.objects.filter(
            created_at__gte=start_date, created_at__lt=end_date
        )

        dies_with_tool_ids = (
            DieTool.objects.filter(die__in=dies_in_range)
            .values_list("die_id", flat=True)
            .distinct()
        )

        total_die_count = Die.objects.filter(deleted=False).count()
        backup_die_counts = dies_in_range.filter(id__in=dies_with_tool_ids).count()
        total_die = dies_in_range.exclude(id__in=dies_with_tool_ids).count()
        total_inquiry_count = Inquiry.objects.filter(deleted=False).count()
        quotation_count = Quotation.objects.filter(
            created_at__gte=start_date, created_at__lt=end_date
        ).count()
        total_workorder_count = WorkOrder.objects.filter(
            deleted=False
        ).count()
        # Today Production Total Kg
        today = timezone.localdate()

        today_production_qs = Production.objects.filter(
            created_at__date=today,
            deleted=False,
        )

        today_production_total_kg = (
            today_production_qs.aggregate(
                total=Coalesce(
                    Sum("total_output_weight"),
                    0.0,
                    output_field=DecimalField(),
                )
            )["total"]
        )
        quotation_converted_count = Quotation.objects.filter(
            status="WorkOrder",
            converted_date__gte=start_date,
            converted_date__lt=end_date,
        ).count()

        # Bundles created in date range
        bundles_created = BundleInward.objects.filter(
            created_at__range=(start_date, end_date)
        )
        bundles_created_count = bundles_created.count()
        bundles_created_pieces = (
            bundles_created.aggregate(total_pieces=Sum("pieces"))["total_pieces"] or 0
        )
        bundles_created_weight = (
            bundles_created.aggregate(total_weight=Sum("weight"))["total_weight"] or 0
        )

        # Bundles dispatched to customer in date range
        bundles_dispatched_customer = BundleInward.objects.filter(
            status="Dispatched",
            added_for_outword=True,
            created_at__range=(start_date, end_date),
        )
        bundles_dispatched_customer_count = bundles_dispatched_customer.count()
        bundles_dispatched_customer_pieces = (
            bundles_dispatched_customer.aggregate(total_pieces=Sum("pieces"))[
                "total_pieces"
            ]
            or 0
        )
        bundles_dispatched_customer_weight = (
            bundles_dispatched_customer.aggregate(total_weight=Sum("weight"))[
                "total_weight"
            ]
            or 0
        )

        # Bundles dispatched to warehouse in date range
        bundles_dispatched_warehouse = BundleInward.objects.filter(
            status="Dispatched",
            added_for_warehouse=True,
            created_at__range=(start_date, end_date),
        )
        bundles_dispatched_warehouse_count = bundles_dispatched_warehouse.count()
        bundles_dispatched_warehouse_pieces = (
            bundles_dispatched_warehouse.aggregate(total_pieces=Sum("pieces"))[
                "total_pieces"
            ]
            or 0
        )
        bundles_dispatched_warehouse_weight = (
            bundles_dispatched_warehouse.aggregate(total_weight=Sum("weight"))[
                "total_weight"
            ]
            or 0
        )

        # Excess Stock
        excess_qs = ExcessStock.objects.filter(created_at__range=(start_date, end_date))
        bundles_moved_to_excess_count = excess_qs.count()
        bundles_moved_to_excess_pieces = excess_qs.aggregate(
            total_pieces=Coalesce(Sum("pieces"), 0)
        )["total_pieces"]
        bundles_moved_to_excess_weight = excess_qs.aggregate(
            total_weight=Coalesce(Sum("weight"), 0, output_field=DecimalField())
        )["total_weight"]

        # Planning
        planning_qs = Planning.objects.filter(
            planning_date__range=(start_date, end_date)
        )
        planning_created_count = planning_qs.count()
        planning_created_plan_pcs = planning_qs.aggregate(
            total=Coalesce(Sum("plan_pcs"), 0)
        )["total"]
        planning_created_plan_qty = planning_qs.aggregate(
            total=Coalesce(Sum("plan_qty"), 0, output_field=DecimalField())
        )["total"]

        # Warehouse
        warehouse_qs = Warehouse.objects.filter(
            created_at__range=(start_date, end_date)
        )
        # Get all finalized bundle IDs from warehouses using new relationships
        finalized_bundle_ids = set()
        for warehouse in warehouse_qs:
            bundle_ids = warehouse.finalized_bundles.values_list("id", flat=True)
            finalized_bundle_ids.update(bundle_ids)

        bundle_qs = BundleInward.objects.filter(id__in=list(finalized_bundle_ids))

        finalized_bundles_count = bundle_qs.count()
        finalized_total_pieces = bundle_qs.aggregate(total=Coalesce(Sum("pieces"), 0))[
            "total"
        ]
        finalized_total_weight = bundle_qs.aggregate(
            total=Coalesce(Sum("weight"), 0.0, output_field=DecimalField())
        )["total"]

        # Graph
        graph_month = request.query_params.get("graph_month")
        graph_year = request.query_params.get("graph_year")

        if not graph_month or not graph_year:
            today = timezone.now()
            graph_month = today.month
            graph_year = today.year
        else:
            graph_month = int(graph_month)
            graph_year = int(graph_year)

        # Get all days in the month
        first_day = date(graph_year, graph_month, 1)
        next_month = first_day.replace(day=28) + timedelta(
            days=4
        )  # ensures we reach next month
        last_day = next_month - timedelta(days=next_month.day)
        num_days = last_day.day

        from collections import OrderedDict

        graph_data = OrderedDict()

        for day in range(1, num_days + 1):
            day_date = date(graph_year, graph_month, day)
            start_day = make_aware(datetime.combine(day_date, datetime.min.time()))
            end_day = start_day + timedelta(days=1)

            # total_kgs: WorkOrderDetail max_weight sum for WorkOrders created that day
            workorders = WorkOrder.objects.filter(
                created_at__range=(start_day, end_day)
            )
            workorder_ids = workorders.values_list("id", flat=True)
            total_kgs = WorkOrderDetail.objects.filter(
                workorder_id__in=workorder_ids
            ).aggregate(
                total=Coalesce(Sum("max_weight"), 0.0, output_field=DecimalField())
            )[
                "total"
            ]

            # total_packing_kgs: BundleInward with status="Packed" and packing_date that day
            total_packing_kgs = BundleInward.objects.filter(
                packing_date__range=(start_day, end_day)
            ).aggregate(
                total=Coalesce(Sum("weight"), 0.0, output_field=DecimalField())
            )[
                "total"
            ]

            # total_dispatched_kgs: BundleInward with status="Dispatched" and dispatch_date that day
            total_dispatched_kgs = BundleInward.objects.filter(
                status="Dispatched", dispatch_date__range=(start_day, end_day)
            ).aggregate(
                total=Coalesce(Sum("weight"), 0.0, output_field=DecimalField())
            )[
                "total"
            ]

            graph_data[day_date.strftime("%d-%m-%Y")] = {
                "total_kgs": float(total_kgs),
                "total_packing_kgs": float(total_packing_kgs),
                "total_dispatched_kgs": float(total_dispatched_kgs),
            }

        return Response(
            {
                "success": True,
                "data": {
                    "total_die_count": total_die_count,  # All dies in range
                    "backup_die_counts": backup_die_counts,  # Dies with tools
                    "total_die": total_die,  # Dies without tools
                    "total_inquiry_count": total_inquiry_count,
                    "quotation_count": quotation_count,
                    "total_workorder_count": total_workorder_count,
                    "quotation_to_workorder_count": quotation_converted_count,
                    "today_production_total_kg": float(today_production_total_kg),
                    "packed_bundles": {
                        "bundles_created_count": bundles_created_count,
                        "bundles_created_pieces": bundles_created_pieces,
                        "bundles_created_weight": float(bundles_created_weight),
                    },
                    "dispatched_to_customer": {
                        "bundles_dispatched_customer_count": bundles_dispatched_customer_count,
                        "bundles_dispatched_customer_pieces": bundles_dispatched_customer_pieces,
                        "bundles_dispatched_customer_weight": float(
                            bundles_dispatched_customer_weight
                        ),
                    },
                    "dispatched_to_warehouse": {
                        "bundles_dispatched_warehouse_count": bundles_dispatched_warehouse_count,
                        "bundles_dispatched_warehouse_pieces": bundles_dispatched_warehouse_pieces,
                        "bundles_dispatched_warehouse_weight": float(
                            bundles_dispatched_warehouse_weight
                        ),
                    },
                    "excess_stock": {
                        "bundles_moved_to_excess_count": bundles_moved_to_excess_count,
                        "bundles_moved_to_excess_pieces": bundles_moved_to_excess_pieces,
                        "bundles_moved_to_excess_weight": float(
                            bundles_moved_to_excess_weight
                        ),
                    },
                    "planning": {
                        "planning_created_count": planning_created_count,
                        "planning_created_plan_pcs": planning_created_plan_pcs,
                        "planning_created_plan_qty": planning_created_plan_qty,
                    },
                    "warehouse_dispatched_bundles": {
                        "warehouse_dispatched_bundles_count": finalized_bundles_count,
                        "warehouse_dispatched_bundles_pieces": finalized_total_pieces,
                        "warehouse_dispatched_bundles_weight": finalized_total_weight,
                    },
                    "graph_data": graph_data,
                },
            }
        )
