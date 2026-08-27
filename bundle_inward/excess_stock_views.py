import logging
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from operator import itemgetter

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from bundle_inward.models import BundleInward, ExcessStock
from bundle_inward.serializers import ExcessStockSerializer
from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from utils.error_handling import custom_exception
from utils.generate_number import BundleNumberGenerator
from utils.log_activity import clean_payload, log_user_activity
from workorder.models import WorkOrderDetail

logger = logging.getLogger("file")

class ExcessStockViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = ExcessStock.objects.all().order_by("-id")
    serializer_class = ExcessStockSerializer

    search_fields = [
        "id",
        "die_profile__die_number",
        "alloy__name",
        "alloy__color_code",
        "temper__name",
        "temper__code",
        "length",
        "weight",
        "gross_weight",
        "pieces",
        "shift",
        "hardness_value",
        "remarks",
    ]

    ordering_fields = [
        "id",
        "die_profile__die_number",
        "alloy__name",
        "alloy__color_code",
        "temper__name",
        "temper__code",
        "length",
        "weight",
        "gross_weight",
        "pieces",
        "shift",
        "hardness_value",
        "remarks",
    ]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        bundle_no = BundleNumberGenerator().generate_bundle_no()

        bundle_data = {
            "shift": data.get("shift"),
            "pieces": data.get("pieces"),
            "weight": data.get("weight"),
            "gross_weight": data.get("gross_weight"),
            "packing_date": timezone.now(),
            "hardness": data.get("hardness_value"),
            "remarks": data.get("remarks"),
            "status": "Packed",
            "is_excess_stock": True,
            "bundle_no": bundle_no,
            "created_by": request.user,
        }

        bundle_inward = BundleInward.objects.create(**bundle_data)

        data["bundle_inward"] = bundle_inward.id

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(created_by=request.user)

            payload = clean_payload(request.data)

            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="excess stock",
                description="Created excess stock",
                request=request,
                payload=payload,
            )

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data.copy()
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True)

            if serializer.is_valid(raise_exception=True):
                serializer.save(updated_by=request.user)

                bundle = instance.bundle_inward
                if bundle:
                    bundle.shift = data.get("shift", bundle.shift)
                    bundle.pieces = data.get("pieces", bundle.pieces)
                    bundle.weight = data.get("weight", bundle.weight)
                    bundle.gross_weight = data.get("gross_weight", bundle.gross_weight)
                    bundle.hardness = data.get("hardness_value", bundle.hardness)
                    bundle.remarks = data.get("remarks", bundle.remarks)
                    bundle.packing_date = timezone.now()
                    bundle.save()

                payload = clean_payload(request.data)
                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="excess stock",
                    description="Updated excess stock",
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

    @action(detail=True, methods=["get"], url_path="excess-stock-by-die-profile")
    def get_excess_stock_by_die_profile(self, request, pk=None):
        """
        Retrieve excess stock by die_profile ID.
        """
        die_profile_id = pk
        queryset = self.get_queryset()
        queryset = queryset.filter(die_profile_id=die_profile_id)

        serializer = self.serializer_class(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="get-excess-stock-bundles-summary")
    def get_excess_stock_bundles_summary(self, request):
        try:
            excess_stocks = ExcessStock.objects.select_related(
                "die_profile", "alloy", "temper"
            ).filter(deleted=False)

            if not excess_stocks.exists():
                return Response(
                    {"success": False, "message": "No excess stock found"},
                    status=status.HTTP_204_NO_CONTENT,
                )

            grouped = defaultdict(list)
            for item in excess_stocks:
                if item.die_profile:
                    grouped[item.die_profile.id].append(item)

            response_data = []

            for die_id, items in grouped.items():
                first_item = items[0]
                die = first_item.die_profile

                total_weight = sum([i.weight for i in items])
                total_pieces = sum([i.pieces for i in items])
                total_bundles = len(items)
                total_weight_str = f"{total_weight:.3f}"

                dimensions = [
                    die.dimension1,
                    die.dimension2,
                    die.dimension3,
                    die.dimension4,
                ]
                dimension_values = [f"{dim:.2f} MM" for dim in dimensions if dim]
                profile_description = (
                    " X ".join(dimension_values)
                    if dimension_values
                    else "No Dimensions Available"
                )

                alloy_name = first_item.alloy.alloy_code if first_item.alloy else None
                alloy_standard = first_item.alloy.standard.name if first_item.alloy.standard else None

                temper_code = first_item.temper.temper_code_new if first_item.temper else None
                temper_standard = first_item.temper.standard.name if first_item.temper.standard else None
                temper_section_type = first_item.temper.section_type if first_item.temper else None
                temper_value = None

                if temper_code and temper_standard:
                    temper_value = f"{temper_code} ({temper_standard})"

                    if temper_section_type:
                        temper_value += f" {temper_section_type}"

                elif temper_code:
                    temper_value = temper_code

                response_data.append(
                    {
                        "profile": die.die_number,
                        "profile_image": die.die_diagram,
                        "profile_description": profile_description,
                        "length": first_item.length,
                        "alloy": f"{alloy_name} ({alloy_standard})" if alloy_name and alloy_standard else alloy_name or None,
                        "temper": temper_value,
                        "total_weight": total_weight_str,
                        "total_pieces": total_pieces,
                        "total_bundles": total_bundles,
                    }
                )

            search_query = request.query_params.get("search", "").lower()
            if search_query:
                response_data = [
                    item
                    for item in response_data
                    if any(
                        [
                            search_query in str(item.get("profile", "")).lower(),
                            search_query in str(item.get("alloy", "")).lower(),
                            search_query in str(item.get("color_code", "")).lower(),
                            search_query in str(item.get("temper", "")).lower(),
                            search_query == str(item.get("length", "")),
                            search_query == str(item.get("total_weight", "")),
                            search_query == str(item.get("total_pieces", "")),
                        ]
                    )
                ]

            ordering = request.query_params.get("ordering", "profile")
            reverse = False
            if ordering.startswith("-"):
                ordering = ordering[1:]
                reverse = True

            try:
                response_data = sorted(
                    response_data, key=itemgetter(ordering), reverse=reverse
                )
            except KeyError:
                pass

            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(response_data, request)

            return paginator.get_paginated_response(
                {"success": True, "data": paginated_data}
            )

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error occurred: {str(e)}"}, status=500
            )

    @action(detail=False, methods=["get"], url_path="excess-stock-bundles")
    def get_excess_stock_bundles(self, request):
        excess_stock_qs = ExcessStock.objects.filter(deleted=False).select_related(
            "die_profile", "alloy", "temper", "bundle_inward"
        )

        bundle_list = []
        for item in excess_stock_qs:
            die = item.die_profile

            if die:
                dimensions = [
                    die.dimension1,
                    die.dimension2,
                    die.dimension3,
                    die.dimension4,
                ]
                dimension_values = [f"{dim} MM" for dim in dimensions if dim]
                profile_description = (
                    " X ".join(dimension_values)
                    if dimension_values
                    else "No Dimensions Available"
                )
            else:
                profile_description = "No Dimensions Available"

            avg_weight = float(item.weight) / item.pieces if item.pieces else 0

            bundle_list.append(
                {
                    "id": item.id,
                    "bundle_no": (
                        item.bundle_inward.bundle_no if item.bundle_inward else None
                    ),
                    "length": item.length,
                    "pieces": item.pieces,
                    "weight": item.weight,
                    "gross_weight": item.gross_weight,
                    "avg_weight": avg_weight,
                    "packing_date": (
                        item.bundle_inward.packing_date if item.bundle_inward else None
                    ),
                    "status": item.bundle_inward.status if item.bundle_inward else None,
                    "profile": die.die_number if die else None,
                    "profile_image": die.die_diagram if die else None,
                    "profile_description": profile_description,
                    "shift": item.shift,
                    "hardness_value": item.hardness_value,
                    "remarks": item.remarks,
                }
            )

        search_query = request.query_params.get("search", "").lower()
        if search_query:
            bundle_list = [
                b
                for b in bundle_list
                if any(
                    search_query in str(b.get(key, "")).lower()
                    for key in [
                        "bundle_no",
                        "profile",
                        "profile_description",
                        "length",
                        "pieces",
                        "weight",
                        "hardness_value",
                        "remarks",
                    ]
                )
            ]

        ordering = request.query_params.get("ordering", "bundle_no")
        reverse = False
        if ordering.startswith("-"):
            ordering = ordering[1:]
            reverse = True

        try:
            bundle_list = sorted(
                bundle_list,
                key=lambda x: (x.get(ordering) is None, x.get(ordering)),
                reverse=reverse,
            )
        except KeyError:
            pass

        page = self.paginate_queryset(bundle_list)
        if page is not None:
            return self.get_paginated_response({"success": True, "data": page})

        return Response({"success": True, "data": bundle_list})

    @action(detail=False, methods=["POST"], url_path="shift-bundles-excess-stock")
    @transaction.atomic
    def shift_bundles_excess_stock(self, request, *args, **kwargs):
        bundle_ids = request.data.get("bundle_id", [])

        if not bundle_ids:
            return Response(
                {"success": False, "message": "No bundle IDs provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bundle_inwards = BundleInward.objects.filter(id__in=bundle_ids)

        if not bundle_inwards.exists():
            return Response(
                {"success": False, "message": "No valid bundle IDs found."},
                status=status.HTTP_204_NO_CONTENT,
            )

        excess_stock_entries = []
        shifted_bundle_nos = []
        for bundle_inward in bundle_inwards:

            if bundle_inward.status == "Dispatched":
                return Response(
                    {
                        "success": False,
                        "message": f"Bundle is already dispatched and cannot be shifted to excess stock.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            excess_stock_entry = ExcessStock(
                die_profile=bundle_inward.workorder_detail.die_profile,
                alloy=bundle_inward.workorder_detail.alloy,
                temper=bundle_inward.workorder_detail.temper,
                bundle_inward=bundle_inward,
                length=bundle_inward.workorder_detail.length,
                weight=bundle_inward.weight,
                gross_weight=bundle_inward.gross_weight,
                pieces=bundle_inward.pieces,
                shift=bundle_inward.shift,
                hardness_value=bundle_inward.hardness,
                remarks=bundle_inward.remarks,
                created_by=request.user,
                created_at=timezone.now(),
            )
            excess_stock_entries.append(excess_stock_entry)

            bundle_inward.is_excess_stock = True
            bundle_inward.save()

            workorder_detail = bundle_inward.workorder_detail
            if workorder_detail:
                total_packed_weight = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail,
                        status="Packed",
                        is_excess_stock=False,
                    ).aggregate(Sum("weight"))["weight__sum"]
                    or 0
                )
                total_packed_pieces = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail,
                        status="Packed",
                        is_excess_stock=False,
                    ).aggregate(Sum("pieces"))["pieces__sum"]
                    or 0
                )

                total_dispatched_weight = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail,
                        status="Dispatched",
                        is_excess_stock=False,
                    ).aggregate(Sum("weight"))["weight__sum"]
                    or 0
                )
                total_dispatched_pieces = (
                    BundleInward.objects.filter(
                        workorder_detail=workorder_detail,
                        status="Dispatched",
                        is_excess_stock=False,
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

                if workorder_detail.pending_pieces == workorder_detail.pieces:
                    workorder_detail.status = "Pending"
                else:
                    workorder_detail.status = "In-Process"

                workorder_detail.save()

            workorder = workorder_detail.workorder
            if workorder:
                details = workorder.workorder_detail_workorder.all()
                if all(
                    (d.packed_pieces or 0) == 0 and (d.dispatched_pieces or 0) == 0
                    for d in details
                ):
                    workorder.status = "Planning"
                else:
                    workorder.status = "Open"
                workorder.save()

            shifted_bundle_nos.append(bundle_inward.bundle_no)

        ExcessStock.objects.bulk_create(excess_stock_entries)

        description = (
            f"Shifted bundles to excess stock : {', '.join(shifted_bundle_nos)}"
        )
        payload = clean_payload(request.data)

        log_user_activity(
            user=request.user,
            action="SHIFT",
            module_name="excess stock",
            description=description,
            request=request,
            payload=payload,
        )

        return Response(
            {
                "success": True,
                "message": "Bundles shifted to excess stock successfully.",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["POST"], url_path="shift-bundles-to-workorder")
    @transaction.atomic
    def shift_bundles_to_workorder(self, request):
        bundle_ids = request.data.get("bundle_ids", [])
        target_wod_id = request.data.get("workorder_detail_id")

        if not bundle_ids or not target_wod_id:
            return Response(
                {
                    "success": False,
                    "message": "Both bundle_ids and workorder_detail_id are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            matched_detail = WorkOrderDetail.objects.select_related(
                "workorder", "die_profile", "alloy", "temper"
            ).get(id=target_wod_id)
            workorder = matched_detail.workorder
        except WorkOrderDetail.DoesNotExist:
            return Response(
                {"success": False, "message": "Target WorkOrderDetail does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success_bundles, failed_bundles, shifted_bundle_nos = [], [], []
        DECIMAL_PRECISION = Decimal("0.001")

        existing = BundleInward.objects.filter(
            workorder_detail=matched_detail
        ).aggregate(total_pieces=Sum("pieces"), total_weight=Sum("weight"))
        shifted_pieces = existing["total_pieces"] or 0
        shifted_weight = existing["total_weight"] or 0

        for bundle in BundleInward.objects.filter(id__in=bundle_ids):
            bundle_no = bundle.bundle_no or "N/A"

            if not bundle.is_excess_stock:
                failed_bundles.append(
                    {
                        "bundle_no": bundle_no,
                        "reason": "Bundle is not marked as excess stock.",
                    }
                )
                continue

            is_match = False
            if bundle.workorder_detail:
                wod = bundle.workorder_detail
                if (
                    wod.die_profile_id == matched_detail.die_profile_id
                    and wod.alloy_id == matched_detail.alloy_id
                    and wod.temper_id == matched_detail.temper_id
                    and wod.length == matched_detail.length
                ):
                    is_match = True
            else:
                excess = ExcessStock.objects.filter(bundle_inward=bundle).first()
                if excess and (
                    excess.die_profile_id == matched_detail.die_profile_id
                    and excess.alloy_id == matched_detail.alloy_id
                    and excess.temper_id == matched_detail.temper_id
                    and excess.length == matched_detail.length
                ):
                    is_match = True

            if not is_match:
                failed_bundles.append(
                    {
                        "bundle_no": bundle_no,
                        "reason": "Bundle properties do not match the selected workorder detail (profile, alloy, temper, length).",
                    }
                )
                continue

            pieces = bundle.pieces or 0
            weight = bundle.weight or 0
            total_ordered_pieces = matched_detail.pieces or 0
            tolerance = matched_detail.workorder.tolerance or "+0%"
            die_over_weight = matched_detail.die_over_weight

            percent = 0
            percent_str = tolerance.replace("+-", "").replace("+", "").replace("%", "")
            if percent_str.isdigit():
                percent = int(percent_str)

            if die_over_weight:
                percent += 10

            remaining_pieces = (
                total_ordered_pieces + int(total_ordered_pieces * percent / 100)
            ) - shifted_pieces

            if pieces > remaining_pieces:
                failed_bundles.append(
                    {
                        "bundle_no": bundle_no,
                        "reason": f"Bundle contains {pieces} pieces, which exceeds the allowed limit. Maximum allowed (including tolerance) is {int(remaining_pieces)} piece(s).",
                    }
                )

                continue

            weight_per_piece = (
                Decimal(matched_detail.die_profile.wt_kg_p_mt)
                * Decimal(matched_detail.length)
                / Decimal(1000)
            ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

            expected_weight = (weight_per_piece * Decimal(pieces)).quantize(
                DECIMAL_PRECISION, rounding=ROUND_HALF_UP
            )
            proportional_tolerance_percent = (
                Decimal(pieces) / Decimal(total_ordered_pieces)
            ) * Decimal(percent)

            max_allowed_weight = (
                expected_weight
                + (expected_weight * proportional_tolerance_percent / Decimal(100))
            ).quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

            payload_weight = Decimal(str(weight)).quantize(
                DECIMAL_PRECISION, rounding=ROUND_HALF_UP
            )

            if die_over_weight:
                base_per_piece = weight_per_piece
                min_per_piece = base_per_piece
                max_per_piece = base_per_piece + (
                    base_per_piece * Decimal(percent) / Decimal(100)
                )
                min_total_weight = (min_per_piece * Decimal(pieces)).quantize(
                    DECIMAL_PRECISION, rounding=ROUND_HALF_UP
                )
                max_total_weight = (max_per_piece * Decimal(pieces)).quantize(
                    DECIMAL_PRECISION, rounding=ROUND_HALF_UP
                )

                if not (min_total_weight <= payload_weight <= max_total_weight):
                    failed_bundles.append(
                        {
                            "bundle_no": bundle_no,
                            "reason": f"Bundle weight {payload_weight} kg is outside the allowed range ({min_total_weight} kg – {max_total_weight} kg) with die over-weight tolerance applied.",
                        }
                    )
                    continue
            else:
                if payload_weight > max_allowed_weight:
                    failed_bundles.append(
                        {
                            "bundle_no": bundle_no,
                            "reason": f"Bundle weight {payload_weight} kg exceeds the maximum allowed weight of {max_allowed_weight} kg based on {proportional_tolerance_percent:.2f}% tolerance.",
                        }
                    )
                    continue

            bundle.workorder = workorder
            bundle.workorder_detail = matched_detail
            bundle.is_excess_stock = False
            bundle.save()

            ExcessStock.objects.filter(bundle_inward=bundle).delete()

            matched_detail.packed_weight = (matched_detail.packed_weight or 0) + weight
            matched_detail.packed_pieces = (matched_detail.packed_pieces or 0) + pieces
            matched_detail.pending_weight = (
                matched_detail.pending_weight or 0
            ) - weight
            matched_detail.pending_pieces = (
                matched_detail.pending_pieces or 0
            ) - pieces

            if BundleInward.objects.filter(workorder_detail=matched_detail).exists():
                matched_detail.status = "In-Process"
            if (
                matched_detail.packed_weight == matched_detail.net_weight
                and matched_detail.packed_pieces == matched_detail.pieces
            ):
                matched_detail.status = "Packed"
            matched_detail.save()

            related_details = WorkOrderDetail.objects.filter(workorder=workorder)
            if all(d.status == "Packed" for d in related_details):
                workorder.status = "Packed"
            else:
                workorder.status = "Open"
            workorder.save()

            success_bundles.append(bundle.id)
            shifted_bundle_nos.append(bundle_no)
            shifted_pieces += pieces
            shifted_weight += weight

        total = len(bundle_ids)
        success = len(success_bundles)
        failed = len(failed_bundles)
        failed_bundle_nos = ", ".join(
            [fb.get("bundle_no", "N/A") for fb in failed_bundles]
        )

        if success and failed:
            message = f"{success} out of {total} bundles were successfully shifted to Work Order {workorder.order_no}. The following {failed} bundle(s) could not be shifted: {failed_bundle_nos}."
        elif success:
            message = f"All {success} bundle(s) were successfully shifted to Work Order {workorder.order_no}."
        else:
            message = f"None of the {total} bundle(s) could be shifted. The following bundle(s) failed: {failed_bundle_nos}."

        if shifted_bundle_nos:
            payload = clean_payload(request.data)
            log_user_activity(
                user=request.user,
                action="SHIFT",
                module_name="excess stock",
                description=f"Shifted bundles: {', '.join(shifted_bundle_nos)}",
                request=request,
                payload=payload,
            )

        return Response(
            {
                "success": bool(success_bundles),
                "message": message,
                "shifted_bundles": success_bundles,
                "unshifted_bundles": failed_bundles,
            }
        )

    @action(detail=False, methods=["get"], url_path="excess-party-print")
    def excess_party_print(self, request):
        excess_stock_id = request.query_params.get("excess_stock_id")
        if not excess_stock_id:
            return Response(
                {"success": False, "message": "excess_stock_id is required"},
                status=400,
            )

        try:
            excess = ExcessStock.objects.select_related(
                "die_profile", "bundle_inward", "alloy", "temper"
            ).get(id=excess_stock_id)
        except ExcessStock.DoesNotExist:
            return Response(
                {"success": False, "message": "ExcessStock not found"}, status=404
            )

        try:
            die = excess.die_profile
            bundle = excess.bundle_inward

            bundle_no = bundle.bundle_no if bundle and bundle.bundle_no else "N/A"
            packing_date = (
                bundle.packing_date.strftime("%Y-%m-%d")
                if bundle and bundle.packing_date
                else "N/A"
            )
            status = bundle.status if bundle and bundle.status else "N/A"

            pieces = excess.pieces or 0

            weight = float(excess.weight) if excess.weight is not None else 0.0
            gross_weight = float(excess.gross_weight) if excess.gross_weight is not None else 0.0

            avg_weight = ExcessStockSerializer().get_avg_weight(excess)
            avg_weight = float(avg_weight) if avg_weight is not None else 0.0

            data = {
                "bundle_no": bundle_no,
                "profile": die.die_number if die else "N/A",
                "customer_reference_no": (
                    die.customer_reference_number if die else "N/A"
                ),
                "profile_description": die.get_item_name() if die else "N/A",
                "die_diagram": die.die_diagram.url if die and die.die_diagram else None,
                "length": excess.length or 0,
                "alloy": excess.alloy.alloy_code if excess.alloy else "N/A",
                "temper": excess.temper.temper_code_new if excess.temper else "N/A",
                "pieces": pieces,
                "weight": f"{weight:.3f}",
                "gross_weight": f"{gross_weight:.3f}",
                "avg_weight": f"{avg_weight:.3f}",
                "packing_date": packing_date,
                "status": status,
            }

            return Response({"success": True, "data": data}, status=200)

        except Exception as e:
            return Response(
                {"success": False, "message": f"Error processing data: {str(e)}"},
                status=500,
            )
