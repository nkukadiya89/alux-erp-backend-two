import logging
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, IntegerField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from bundle_inward.models import BundleInward   
from bundle_inward.serializers import BundleInwardSerializer
from bundle_inward.sort_serializers import BundleInwardListSerializer
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin, FinancialYearModel
from utils.error_handling import custom_exception, custom_exception_unique
from utils.log_activity import clean_payload, log_user_activity
from workorder.models import WorkOrder, WorkOrderDetail

logger = logging.getLogger("file")


class BundleInwardViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = BundleInward.objects.filter(deleted=False).order_by("-id")
    serializer_class = BundleInwardSerializer
    list_serializer_class = BundleInwardListSerializer

    search_fields = [
        "id",
        "workorder__order_no",
        "workorder__bill_to__customer_name",
        "bundle_no",
    ]

    ordering_fields = [
        "id",
        "workorder__order_no",
        "workorder__bill_to__customer_name",
        "bundle_no",
        "gross_weight",
        "packing_date",
    ]

    def get_queryset(self):
        qs = (
            BundleInward.objects.filter(deleted=False)
            .select_related(
                "workorder", "workorder_detail", "verify_by", "created_by", "updated_by"
            )
            .prefetch_related("excess_stock_bundle_inward")
            .order_by("-id")
        )

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        date_format = "%d-%m-%Y"
        try:
            if start_date:
                start = datetime.strptime(start_date, date_format)
                start = timezone.make_aware(start, timezone.get_current_timezone())
                qs = qs.filter(packing_date__gte=start)
            if end_date:
                end = datetime.strptime(end_date, date_format)
                end = end.replace(hour=23, minute=59, second=59)
                end = timezone.make_aware(end, timezone.get_current_timezone())
                qs = qs.filter(packing_date__lte=end)
        except ValueError:
            raise ValidationError("Date format must be DD-MM-YYYY.")

        fy_id = self.request.query_params.get("fy_id")
        if fy_id:
            try:
                fy = FinancialYearModel.objects.get(fid=fy_id)
                qs = qs.filter(
                    created_at__gte=fy.start_date, created_at__lte=fy.end_date
                )
            except FinancialYearModel.DoesNotExist:
                pass
                return qs.none()
        else:
            current_fy = FinancialYearModel.objects.filter(current=True).first()
            if current_fy and current_fy.start_date and current_fy.end_date:
                qs = qs.filter(
                    created_at__gte=current_fy.start_date,
                    created_at__lte=current_fy.end_date,
                )

        qs = qs.exclude(is_excess_stock=True)
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        serializer = self.serializer_class(data=data)

        try:
            if serializer.is_valid(raise_exception=True):
                workorder_id = data.get("workorder")
                workorder_detail_id = data.get("workorder_detail")

                existing_bundles = BundleInward.objects.filter(
                    workorder_id=workorder_id
                ).exists()
                if not existing_bundles:
                    workorder = WorkOrder.objects.get(id=workorder_id)
                    workorder.status = "Open"
                    workorder.save()

                if workorder_detail_id:
                    try:
                        workorder_detail = WorkOrderDetail.objects.get(
                            id=workorder_detail_id
                        )
                        workorder_detail.status = "In-Process"
                        workorder_detail.save()
                        try:
                            from workorder.process_tracking import advance_process

                            advance_process(
                                workorder_detail=workorder_detail,
                                stage="WAITING_FOR_PACKING",
                                user=request.user,
                                remarks="Bundle inward started",
                            )
                        except Exception:
                            pass
                    except WorkOrderDetail.DoesNotExist:
                        logger.error(
                            f"WorkOrderDetail with id {workorder_detail_id} does not exist."
                        )
                        return Response(
                            {"success": False, "message": "WorkOrderDetail not found."},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                bundle_inward = serializer.save(created_by=request.user)

                total_packed_weight = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail, status="Packed"
                    ).aggregate(Sum("weight"))["weight__sum"]
                    or 0
                )
                total_packed_pieces = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail, status="Packed"
                    ).aggregate(Sum("pieces"))["pieces__sum"]
                    or 0
                )

                total_dispatched_weight = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail, status="Dispatched"
                    ).aggregate(Sum("weight"))["weight__sum"]
                    or 0
                )
                total_dispatched_pieces = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail, status="Dispatched"
                    ).aggregate(Sum("pieces"))["pieces__sum"]
                    or 0
                )

                workorder_detail.packed_weight = total_packed_weight
                workorder_detail.packed_pieces = total_packed_pieces
                workorder_detail.dispatched_weight = total_dispatched_weight
                workorder_detail.dispatched_pieces = total_dispatched_pieces

                workorder_detail.pending_weight = (
                    workorder_detail.net_weight
                    - total_packed_weight
                    - total_dispatched_weight
                )
                workorder_detail.pending_pieces = (
                    workorder_detail.pieces
                    - total_packed_pieces
                    - total_dispatched_pieces
                )

                # Fulfillment = order qty met; tolerance only caps max allowed pack qty.
                from utils.packing_tolerance import is_quantity_fulfilled

                cumulative_pcs = total_packed_pieces + total_dispatched_pieces
                cumulative_weight = Decimal(str(total_packed_weight or 0)) + Decimal(
                    str(total_dispatched_weight or 0)
                )

                if is_quantity_fulfilled(
                    cumulative_pcs, cumulative_weight, workorder_detail
                ):
                    workorder_detail.status = "Packed"
                    workorder_detail.save()
                    try:
                        from workorder.process_tracking import advance_process

                        advance_process(
                            workorder_detail=workorder_detail,
                            stage="PACKED",
                            user=request.user,
                            remarks="Bundle inward order qty fulfilled (WO tolerance applies to max allowed)",
                        )
                    except Exception:
                        pass
                else:
                    # Keep In-Process while packing is underway (first bundle already
                    # advanced WAITING_FOR_PACKING above).
                    if workorder_detail.status != "Packed":
                        workorder_detail.status = "In-Process"
                    workorder_detail.save()

                all_details_packed = (
                    not WorkOrderDetail.objects.filter(workorder_id=workorder_id)
                    .exclude(status="Packed")
                    .exists()
                )

                if all_details_packed:
                    workorder = WorkOrder.objects.get(id=workorder_id)
                    workorder.status = "Packed"
                    workorder.save()

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="BundleInward",
                    description=f"Created bundle inward {bundle_inward.bundle_no}",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )

            else:
                logger.error(f"Error in creating record : {serializer.errors}")
                return Response(
                    {"success": False, "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return custom_exception_unique(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True)

            if serializer.is_valid(raise_exception=True):
                instance = serializer.save(updated_by=request.user)
                logger.info("Record updated successfully.")

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="BundleInward",
                    description=f"Updated bundle inward {instance.bundle_no}",
                    request=request,
                    payload=payload,
                )

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

    @action(
        detail=False, methods=["delete"], url_path="delete-bundle/(?P<bundle_id>\\d+)"
    )
    @transaction.atomic
    def delete_bundle(self, request, bundle_id=None):
        try:
            bundle = BundleInward.objects.filter(id=bundle_id).first()
            if not bundle:
                return Response(
                    {"success": False, "message": "Bundle not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            workorder_detail = bundle.workorder_detail
            if not workorder_detail:
                return Response(
                    {
                        "success": False,
                        "message": "WorkOrderDetail not associated with this bundle.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            workorder = workorder_detail.workorder

            bundle.delete()

            total_packed_weight = (
                BundleInward.objects.filter(
                    workorder_detail=workorder_detail, status="Packed"
                ).aggregate(Sum("weight"))["weight__sum"]
                or 0
            )
            total_packed_pieces = (
                BundleInward.objects.filter(
                    workorder_detail=workorder_detail, status="Packed"
                ).aggregate(Sum("pieces"))["pieces__sum"]
                or 0
            )

            total_dispatched_weight = (
                BundleInward.objects.filter(
                    workorder_detail=workorder_detail, status="Dispatched"
                ).aggregate(Sum("weight"))["weight__sum"]
                or 0
            )
            total_dispatched_pieces = (
                BundleInward.objects.filter(
                    workorder_detail=workorder_detail, status="Dispatched"
                ).aggregate(Sum("pieces"))["pieces__sum"]
                or 0
            )

            workorder_detail.packed_weight = total_packed_weight
            workorder_detail.packed_pieces = total_packed_pieces
            workorder_detail.dispatched_weight = total_dispatched_weight
            workorder_detail.dispatched_pieces = total_dispatched_pieces

            workorder_detail.pending_weight = (
                workorder_detail.net_weight
                - total_packed_weight
                - total_dispatched_weight
            )
            workorder_detail.pending_pieces = (
                workorder_detail.pieces - total_packed_pieces - total_dispatched_pieces
            )

            if workorder_detail.pending_pieces == workorder_detail.pieces:
                workorder_detail.status = "Pending"
            elif (
                workorder_detail.pending_pieces <= 0
                and total_packed_pieces >= workorder_detail.pieces
            ):
                workorder_detail.status = "Packed"
            else:
                workorder_detail.status = "In-Process"

            workorder_detail.save()

            if workorder:
                all_details = workorder.workorder_detail_workorder.all()

                if all(d.status == "Pending" for d in all_details):
                    workorder.status = "Planning"
                elif all(d.status == "Packed" for d in all_details):
                    workorder.status = "Packed"
                elif all(d.status == "Dispatched" for d in all_details):
                    workorder.status = "Dispatched"
                else:
                    workorder.status = "Open"

                workorder.save()

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="DELETE",
                module_name="BundleInward",
                description=f"Deleted bundle inward {bundle.bundle_no}",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "message": "Bundle deleted successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return custom_exception(e)

    @action(detail=True, methods=["GET"], url_path="bundle-inward-by-workorder")
    def bundle_by_workorder(self, request, pk=None, *args, **kwargs):
        try:
            order_aggregate = WorkOrderDetail.objects.filter(workorder_id=pk).aggregate(
                total_pieces=Coalesce(
                    Sum("pieces"), Value(0), output_field=IntegerField()
                ),
                total_weight=Coalesce(
                    Sum("net_weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )
            total_order_pieces = order_aggregate["total_pieces"]
            total_order_weight = float(order_aggregate["total_weight"])

            bundles = (
                self.queryset.filter(workorder_id=pk, is_excess_stock=False)
                .select_related("workorder_detail__die_profile")
                .order_by("-id")
            )

            if not bundles.exists():
                return Response(
                    {
                        "success": True,
                        "data": {
                            "bundles": [],
                            "order": {
                                "pieces": total_order_pieces,
                                "weight": f"{total_order_weight:.3f}",
                            },
                            "packed": {"pieces": 0, "weight": "0.000"},
                            "dispatched": {"pieces": 0, "weight": "0.000"},
                            "pending": {
                                "pieces": total_order_pieces,
                                "weight": f"{total_order_weight:.3f}",
                            },
                        },
                    },
                    status=status.HTTP_200_OK,
                )

            completed_agg = bundles.filter(
                status__in=["Packed", "Dispatched"]
            ).aggregate(
                pieces=Coalesce(Sum("pieces"), Value(0), output_field=IntegerField()),
                weight=Coalesce(
                    Sum("weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )

            packed_agg = bundles.filter(status="Packed").aggregate(
                pieces=Coalesce(Sum("pieces"), Value(0), output_field=IntegerField()),
                weight=Coalesce(
                    Sum("weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )

            dispatched_agg = bundles.filter(status="Dispatched").aggregate(
                pieces=Coalesce(Sum("pieces"), Value(0), output_field=IntegerField()),
                weight=Coalesce(
                    Sum("weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )

            total_completed_pieces = completed_agg["pieces"]
            total_completed_weight = float(completed_agg["weight"])

            total_packed_pieces = packed_agg["pieces"]
            total_packed_weight = float(packed_agg["weight"])
            total_dispatched_pieces = dispatched_agg["pieces"]
            total_dispatched_weight = float(dispatched_agg["weight"])

            pending_pieces = max(total_order_pieces - total_completed_pieces, 0)
            pending_weight = max(total_order_weight - total_completed_weight, 0)

            simplified_data = []
            for bundle in bundles:
                wod = bundle.workorder_detail
                dp = wod.die_profile if wod else None

                dims = [
                    str(getattr(dp, f"dimension{i}", ""))
                    for i in range(1, 5)
                    if getattr(dp, f"dimension{i}", "")
                ]
                dimension_str = " X ".join(dims) if dims else "-"

                avg_weight = 0.0
                if bundle.pieces and bundle.pieces > 0 and bundle.weight:
                    avg_weight = round(float(bundle.weight) / bundle.pieces, 3)

                simplified_data.append(
                    {
                        "id": bundle.id,
                        "bundle_no": bundle.bundle_no,
                        "die_number": dp.die_number if dp else None,
                        "length": wod.length if wod else None,
                        "dimensions": dimension_str,
                        "pieces": bundle.pieces or 0,
                        "weight": f"{float(bundle.weight or 0):.3f}",
                        "avg_weight": f"{avg_weight:.3f}",
                        "packing_date": bundle.packing_date,
                        "status": bundle.status,
                    }
                )

            return Response(
                {
                    "success": True,
                    "data": {
                        "bundles": simplified_data,
                        "order": {
                            "pieces": total_order_pieces,
                            "weight": f"{total_order_weight:.3f}",
                        },
                        "packed": {
                            "pieces": total_packed_pieces,
                            "weight": f"{total_packed_weight:.3f}",
                        },
                        "dispatched": {
                            "pieces": total_dispatched_pieces,
                            "weight": f"{total_dispatched_weight:.3f}",
                        },
                        "pending": {
                            "pieces": pending_pieces,
                            "weight": f"{pending_weight:.3f}",
                        },
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)

    @action(detail=True, methods=["GET"], url_path="bundle-inward-by-workorder-detail")
    def bundle_by_workorder_detail(self, request, pk=None, *args, **kwargs):
        if not pk:
            return Response(
                {"success": False, "message": "workorder_detail_id is required"},
                status=400,
            )

        try:
            workorder_detail = WorkOrderDetail.objects.select_related(
                "die_profile"
            ).get(id=pk)

            order_pieces = workorder_detail.pieces or 0
            order_weight = workorder_detail.net_weight or 0

            bundles = (
                BundleInward.objects.filter(
                    workorder_detail_id=pk, is_excess_stock=False
                )
                .select_related("workorder_detail__die_profile")
                .order_by("-id")
            )

            if not bundles.exists():
                return Response(
                    {
                        "success": True,
                        "data": {
                            "bundles": [],
                            "order": {"pieces": order_pieces, "weight": order_weight},
                            "packed": {"pieces": 0, "weight": 0},
                            "dispatched": {"pieces": 0, "weight": 0},
                            "pending": {"pieces": order_pieces, "weight": order_weight},
                        },
                    },
                    status=status.HTTP_200_OK,
                )

            completed_agg = bundles.filter(
                status__in=["Packed", "Dispatched"]
            ).aggregate(
                total_pieces=Coalesce(
                    Sum("pieces"), Value(0), output_field=IntegerField()
                ),
                total_weight=Coalesce(
                    Sum("weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )

            packed_agg = bundles.filter(status="Packed").aggregate(
                total_pieces=Coalesce(
                    Sum("pieces"), Value(0), output_field=IntegerField()
                ),
                total_weight=Coalesce(
                    Sum("weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )

            dispatched_agg = bundles.filter(status="Dispatched").aggregate(
                total_pieces=Coalesce(
                    Sum("pieces"), Value(0), output_field=IntegerField()
                ),
                total_weight=Coalesce(
                    Sum("weight"),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=3),
                ),
            )

            total_packed_pieces = packed_agg["total_pieces"] or 0
            total_packed_weight = packed_agg["total_weight"] or 0
            total_dispatched_pieces = dispatched_agg["total_pieces"] or 0
            total_dispatched_weight = dispatched_agg["total_weight"] or 0

            total_completed_pieces = completed_agg["total_pieces"] or 0
            total_completed_weight = completed_agg["total_weight"] or 0

            pending_pieces = max(order_pieces - total_completed_pieces, 0)
            pending_weight = max(order_weight - total_completed_weight, 0)

            workorder_detail.packed_pieces = total_packed_pieces
            workorder_detail.packed_weight = total_packed_weight
            workorder_detail.dispatched_pieces = total_dispatched_pieces
            workorder_detail.dispatched_weight = total_dispatched_weight
            workorder_detail.save(
                update_fields=[
                    "packed_pieces",
                    "packed_weight",
                    "dispatched_pieces",
                    "dispatched_weight",
                ]
            )

            simplified_data = []
            for bundle in bundles:
                wod = bundle.workorder_detail
                dp = wod.die_profile if wod else None

                dimension_parts = [
                    str(d)
                    for d in [
                        getattr(dp, "dimension1", None),
                        getattr(dp, "dimension2", None),
                        getattr(dp, "dimension3", None),
                        getattr(dp, "dimension4", None),
                    ]
                    if d is not None
                ]
                dimension_str = " X ".join(dimension_parts) if dimension_parts else "-"

                avg_weight = 0.0
                if bundle.pieces and bundle.pieces > 0 and bundle.weight:
                    avg_weight = round(float(bundle.weight) / bundle.pieces, 3)

                simplified_data.append(
                    {
                        "id": bundle.id,
                        "bundle_no": bundle.bundle_no,
                        "die_number": dp.die_number if dp else None,
                        "length": wod.length if wod else None,
                        "dimensions": dimension_str,
                        "pieces": bundle.pieces or 0,
                        "weight": float(bundle.weight or 0),
                        "avg_weight": avg_weight,
                        "packing_date": bundle.packing_date,
                        "status": bundle.status,
                    }
                )

            return Response(
                {
                    "success": True,
                    "data": {
                        "bundles": simplified_data,
                        "order": {
                            "pieces": order_pieces,
                            "weight": float(order_weight),
                        },
                        "packed": {
                            "pieces": total_packed_pieces,
                            "weight": float(total_packed_weight),
                        },
                        "dispatched": {
                            "pieces": total_dispatched_pieces,
                            "weight": float(total_dispatched_weight),
                        },
                        "pending": {
                            "pieces": pending_pieces,
                            "weight": round(float(pending_weight), 3),
                        },
                    },
                },
                status=status.HTTP_200_OK,
            )

        except WorkOrderDetail.DoesNotExist:
            return Response(
                {"success": False, "message": "WorkOrderDetail not found."}, status=404
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)

    @action(detail=False, methods=["get"], url_path="packing-report")
    def packing_report(self, request):
        try:
            shift = request.query_params.get("shift", "").upper()
            start = request.query_params.get("start_date")
            end = request.query_params.get("end_date")

            bundles = BundleInward.objects.filter(deleted=False)

            # Filter by date range if provided
            if start and end:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end, "%Y-%m-%d").date()
                    bundles = bundles.filter(
                        packing_date__date__range=(start_date, end_date)
                    )
                except ValueError:
                    return Response(
                        {"status": False, "message": "Invalid date format", "data": []},
                        status=400,
                    )

            # Aggregate shift-wise weights
            shift_data = {}
            for b in bundles:
                if not b.packing_date:
                    continue

                dt = b.packing_date
                if timezone.is_aware(dt):
                    dt = timezone.localtime(dt)

                report_date = dt.date()
                shift_key = b.shift  # Use shift from model directly
                weight = float(b.weight or 0)

                key = str(report_date)
                if key not in shift_data:
                    shift_data[key] = {"A": 0.0, "B": 0.0}
                shift_data[key][shift_key] += weight

            # Prepare response data
            data = []
            for date_str in sorted(shift_data.keys()):
                a_weight = shift_data[date_str]["A"]
                b_weight = shift_data[date_str]["B"]

                if shift == "A":
                    data.append(
                        {
                            "date": date_str,
                            "shift_a": f"{a_weight:.2f}",
                            "total": f"{a_weight:.2f}",
                        }
                    )
                elif shift == "B":
                    data.append(
                        {
                            "date": date_str,
                            "shift_b": f"{b_weight:.2f}",
                            "total": f"{b_weight:.2f}",
                        }
                    )
                else:
                    total = a_weight + b_weight
                    data.append(
                        {
                            "date": date_str,
                            "shift_a": f"{a_weight:.2f}",
                            "shift_b": f"{b_weight:.2f}",
                            "total": f"{total:.2f}",
                        }
                    )

            return Response(
                {"status": True, "message": "Packing report fetched", "data": data},
                status=200,
            )

        except Exception as e:
            return Response(
                {"status": False, "message": str(e), "data": []}, status=500
            )

    @action(detail=False, methods=["get"], url_path="inward-party-print")
    def party_print(self, request):
        bundle_inward_id = request.query_params.get("bundle_inward_id")
        if not bundle_inward_id:
            return Response(
                {"success": False, "message": "bundle_inward_id is required"},
                status=400,
            )

        try:
            bundle = BundleInward.objects.get(id=bundle_inward_id)
        except BundleInward.DoesNotExist:
            return Response(
                {"success": False, "message": "BundleInward not found"}, status=404
            )

        try:
            wod = bundle.workorder_detail
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "WorkOrderDetail not found for this bundle",
                },
                status=404,
            )

        try:
            die = wod.die_profile
        except Exception:
            return Response(
                {"success": False, "message": "Die not found for this WorkOrderDetail"},
                status=404,
            )

        try:
            surface_finish = list(wod.surface_finish.values_list("name", flat=True))

            data = {
                "bundle_no": bundle.bundle_no,
                "workorder_no": bundle.workorder.order_no,
                "workorder_type": wod.workorder.workorder_type,
                "packing_date": bundle.packing_date,
                "length": wod.length,
                "alloy_code": wod.alloy.alloy_code if wod.alloy else None,
                "temper": wod.temper.temper_code_new if wod.temper else None,
                "net_weight": bundle.weight,
                "gross_weight": bundle.gross_weight,
                "pieces": bundle.pieces,
                "die_number": die.die_number,
                "die_diagram": die.die_diagram if die.die_diagram else None,
                "customer_reference_no": wod.customer_reference_number,
                "packing_type": list(
                    wod.workorder.packing_mode.values_list("name", flat=True)
                ),
                "surface_finish": {
                    "surface_finish": surface_finish,
                    "cutting": wod.cutting,
                    "machining": wod.machining,
                    "deburring": wod.deburring,
                    "anodising": wod.anodising,
                    "powder_coating": wod.powder_coating,
                    "pvdf": wod.pvdf,
                    "out_source": wod.out_source,
                },
            }
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error processing data: {str(e)}"},
                status=500,
            )

        return Response({"success": True, "data": data}, status=200)

    @action(detail=False, methods=["get"], url_path="packing-date-wise")
    def packing_date_wise(self, request):
        from datetime import datetime

        from django.db import connection

        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        sql = """
        SELECT 
            CASE 
                WHEN bi.is_excess_stock = true THEN 'Excess Stock'
                ELSE wo.order_no
            END as workorder_no,
            CASE 
                WHEN bi.is_excess_stock = true THEN 'Excess Stock'
                ELSE c.customer_name
            END as party,
            DATE(bi.packing_date) as date,
            COALESCE(
                CASE WHEN bi.is_excess_stock = true THEN es_die.die_number ELSE wod_die.die_number END,
                'N/A'
            ) as section,
            CASE 
                WHEN bi.is_excess_stock = true THEN es.length
                ELSE wod.length
            END as length,
            CASE 
                WHEN bi.is_excess_stock = true THEN es.weight
                ELSE bi.weight
            END as weight,
            CASE 
                WHEN bi.is_excess_stock = true THEN es.pieces
                ELSE bi.pieces
            END as pieces,
            CASE 
                WHEN bi.is_excess_stock = true THEN 
                    CONCAT_WS(' X ', 
                        CASE WHEN es_die.dimension1 IS NOT NULL THEN CONCAT(es_die.dimension1, ' MM') END,
                        CASE WHEN es_die.dimension2 IS NOT NULL THEN CONCAT(es_die.dimension2, ' MM') END,
                        CASE WHEN es_die.dimension3 IS NOT NULL THEN CONCAT(es_die.dimension3, ' MM') END,
                        CASE WHEN es_die.dimension4 IS NOT NULL THEN CONCAT(es_die.dimension4, ' MM') END
                    )
                ELSE 
                    CONCAT_WS(' X ', 
                        CASE WHEN wod_die.dimension1 IS NOT NULL THEN CONCAT(wod_die.dimension1, ' MM') END,
                        CASE WHEN wod_die.dimension2 IS NOT NULL THEN CONCAT(wod_die.dimension2, ' MM') END,
                        CASE WHEN wod_die.dimension3 IS NOT NULL THEN CONCAT(wod_die.dimension3, ' MM') END,
                        CASE WHEN wod_die.dimension4 IS NOT NULL THEN CONCAT(wod_die.dimension4, ' MM') END
                    )
            END as item_name
        FROM bundle_inward bi
        LEFT JOIN workorder wo ON bi.workorder_id = wo.id
        LEFT JOIN customer_customer c ON wo.bill_to_id = c.id
        LEFT JOIN workorder_detail wod ON bi.workorder_detail_id = wod.id
        LEFT JOIN die wod_die ON wod.die_profile_id = wod_die.id
        LEFT JOIN excess_stock es ON bi.id = es.bundle_inward_id
        LEFT JOIN die es_die ON es.die_profile_id = es_die.id
        WHERE 1=1
        """
        deleted = request.query_params.get("deleted")

        if deleted == "0":
            sql += " AND bi.deleted = FALSE"
        elif deleted == "1":
            sql += " AND bi.deleted = TRUE"
        else:
            sql += " AND bi.deleted = FALSE"

        params = []
        if from_date and to_date:
            try:
                start = datetime.strptime(from_date, "%Y-%m-%d").date()
                end = datetime.strptime(to_date, "%Y-%m-%d").date()
                sql += " AND DATE(bi.packing_date) BETWEEN %s AND %s"
                params.extend([start, end])
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid date format. Use YYYY-MM-DD",
                    },
                    status=400,
                )

        sql += " ORDER BY bi.packing_date"

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            response_data = []
            for row in results:
                weight_val = float(row["weight"] or 0)
                response_data.append(
                    {
                        "workorder_no": row["workorder_no"] or "N/A",
                        "section": row["section"] or "N/A",
                        "date": row["date"].strftime("%Y-%m-%d") if row["date"] else "",
                        "party": row["party"] or "N/A",
                        "length": row["length"] or 0,
                        "item_name": row["item_name"] or "N/A",
                        "packed_wt": f"{weight_val:.3f}",
                        "packed_pc": row["pieces"] or 0,
                    }
                )

            return Response({"success": True, "data": response_data}, status=200)

        except Exception as e:
            return Response(
                {"success": False, "message": f"Database error: {str(e)}"},
                status=500,
            )


