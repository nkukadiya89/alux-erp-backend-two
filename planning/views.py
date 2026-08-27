from decimal import Decimal
from django.db import transaction
from django.db.models import (
    Prefetch,
    Sum,
    Q,
    F,
    Value,
    IntegerField,
    OuterRef,
    Subquery,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from die_requisition.models import DieRequisitionDetail
from planning.models import Planning
from planning.serializers import (
    PlanningListSerializer,
    PlanningSerializers,
    PlanningStatusUpdateSerializer,
)
from production.models import Production
from utils.error_handling import custom_exception
from utils.generate_number import generate_planning_no
from utils.log_activity import clean_payload, log_user_activity
from workorder.models import WorkOrderDetail


class PlanningViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Planning.objects.filter(deleted=False)
        .select_related(
            "profile_no",
            "workorder",
            "workorder__bill_to",
            "workorder__created_by",
            "workorder__updated_by",
            "workorder_detail",
            "workorder_detail__die_profile",
            "workorder_detail__alloy",
            "workorder_detail__alloy__standard",
            "workorder_detail__temper",
            "workorder_detail__temper__standard",
            "workorder_detail__temper__section_type",
            "ageing",
            "die_requisition",
            "die_requisition_detail",
            "die_requisition_detail__die_tool",
            "die_requisition_detail__die_tool__eligible_for_press",
            "die_requisition_detail__press",
            "created_by",
            "updated_by",
        )
        .prefetch_related(
            Prefetch(
                "die_requisition__die_requisition",
                queryset=DieRequisitionDetail.objects.filter(deleted=False)
                .select_related(
                    "die_tool",
                    "die_tool__eligible_for_press",
                    "press",
                )
                .order_by("id"),
            )
        )
        .order_by("-id")
    )
    serializer_class = PlanningSerializers
    list_serializer_class = PlanningListSerializer

    search_fields = [
        "planning_no",                                    # Planning No
        "planning_date",
        "plan_pcs",
        "plan_qty",
        "status",
        "quenching_type",
        "remarks",
        "ageing__cycle_name",                             # Ageing (not FK itself)
        "ageing__cycle_code",
        "workorder__order_no",                            # Workorder / IWO No
        "workorder__purchase_order_no",
        "workorder__bill_to__customer_name",              # Customer
        "workorder__bill_to__code",
        "profile_no__die_number",                         # Section No
        "workorder_detail__die_profile__die_number",
        "workorder_detail__alloy__alloy_code",            # Alloy
        "workorder_detail__temper__temper_code_new",      # Temper
        "workorder_detail__length",                       # Cut Length
        "die_requisition__requisition_no",
        "die_requisition_detail__press__name",            # Press No
        "die_requisition_detail__press__code",
        "die_requisition_detail__die_tool__tool_number",  # Die Tool No
    ]

    ordering_fields = [
        "id",
        "planning_no",
        "planning_date",
        "plan_pcs",
        "plan_qty",
        "status",
        "ageing__cycle_name",
        "workorder__order_no",
        "workorder__bill_to__customer_name",
        "profile_no__die_number",
        "die_requisition_detail__press__name",
        "created_at",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Annotate produced pcs once for list/archive (avoids N+1 production queries)
        if getattr(self, "action", None) in ("list", "archive_list"):
            produced_subq = (
                Production.objects.filter(
                    planning_id=OuterRef("pk"),
                    deleted=False,
                )
                .values("planning_id")
                .annotate(total=Sum("actual_pieces"))
                .values("total")[:1]
            )
            queryset = queryset.annotate(
                produced_pcs_sum=Coalesce(
                    Subquery(produced_subq, output_field=IntegerField()),
                    Value(0),
                )
            )

        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        data["planning_no"] = generate_planning_no(self)
        data["created_at"] = timezone.now()
        data["updated_at"] = None

        try:
            workorder_detail_id = data.get("workorder_detail_id")
            plan_qty = Decimal(str(data.get("plan_qty", 0)))
            plan_pcs = int(data.get("plan_pcs", 0))

            if not workorder_detail_id:
                return Response(
                    {"success": False, "message": "workorder_detail_id is required."},
                    status=400,
                )

            try:
                workorder_detail = WorkOrderDetail.objects.get(id=workorder_detail_id)
            except WorkOrderDetail.DoesNotExist:
                return Response(
                    {"success": False, "message": "WorkOrderDetail not found."},
                    status=400,
                )

            current_weight = Decimal(str(workorder_detail.die_profile.wt_kg_p_mt or 0))
            length = Decimal(str(workorder_detail.length or 0))
            net_weight = Decimal(str(workorder_detail.net_weight or 0))
            tolerance = workorder_detail.workorder.tolerance

            total_planned_weight = Decimal(
                str(
                    Planning.objects.filter(
                        workorder_detail=workorder_detail
                    ).aggregate(Sum("plan_qty"))["plan_qty__sum"]
                    or 0
                )
            )
            total_planned_pcs = (
                Planning.objects.filter(workorder_detail=workorder_detail).aggregate(
                    Sum("plan_pcs")
                )["plan_pcs__sum"]
                or 0
            )

            allowed_weight = net_weight
            if tolerance:
                percent = int(
                    tolerance.replace("+-", "").replace("+", "").replace("%", "")
                )
                allowed_weight += net_weight * Decimal(percent) / 100

            remaining_weight = allowed_weight - total_planned_weight

            max_pieces = (
                allowed_weight / (current_weight * (length / 1000))
                if current_weight and length
                else 0
            )
            remaining_pieces = int(max_pieces - total_planned_pcs)
            if (
                total_planned_weight > 0
                and total_planned_weight + plan_qty > allowed_weight
            ):
                remaining_weight_allowed = allowed_weight - total_planned_weight

                if remaining_weight_allowed <= 0:
                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"Planning not allowed. This workorder item is already fully planned "
                                f"({total_planned_weight} kg) as per allowed tolerance ({tolerance or '0%'})."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"Cannot create planning. Already planned: {total_planned_weight} kg. "
                                f"You can only plan {round(remaining_weight_allowed, 2)} kg more as per tolerance ({tolerance or '0%'})."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if total_planned_pcs > 0 and total_planned_pcs + plan_pcs > max_pieces:
                remaining_pcs_allowed = int(max_pieces - total_planned_pcs)

                if remaining_pcs_allowed <= 0:
                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"Planning not allowed. This workorder item is already fully planned "
                                f"({total_planned_pcs} pcs) as per allowed tolerance ({tolerance or '0%'})."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"Cannot create planning. Already planned: {total_planned_pcs} pcs. "
                                f"You can only plan {remaining_pcs_allowed} pcs more as per tolerance ({tolerance or '0%'})."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if plan_qty > remaining_weight:
                if remaining_weight <= 0:
                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"Planning not allowed. Maximum allowed weight is already planned as per tolerance ({tolerance or '0%'})."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(
                    {
                        "success": False,
                        "message": f"Plan qty too high. Max allowed: {round(remaining_weight, 2)} kg as per tolerance ({tolerance or '0%'}).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if plan_pcs > remaining_pieces:
                if remaining_pieces <= 0:
                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"Planning not allowed. Maximum allowed pieces are already planned as per tolerance ({tolerance or '0%'})."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(
                    {
                        "success": False,
                        "message": f"Cannot create planning with {plan_pcs} pcs. Max allowed: {remaining_pieces} pcs.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data["workorder_detail"] = workorder_detail.id

            serializer = self.serializer_class(data=data, context={"request": request})

            if serializer.is_valid():
                planning_instance = serializer.save(created_by=request.user)

                workorder_detail.palnning_weight = (
                    workorder_detail.palnning_weight or 0
                ) + plan_qty
                workorder_detail.planning_pieces = (
                    workorder_detail.planning_pieces or 0
                ) + plan_pcs

                try:
                    percent = int(str(tolerance).replace("+-", "").replace("%", ""))
                except Exception:
                    percent = 0

                tolerance_multiplier = 1 + (Decimal(percent) / 100)
                max_allowed_weight = net_weight * tolerance_multiplier
                max_allowed_pcs = (workorder_detail.pieces or 0) * tolerance_multiplier

                if (
                    workorder_detail.palnning_weight >= net_weight
                    and workorder_detail.palnning_weight <= max_allowed_weight
                    and workorder_detail.planning_pieces
                    >= (workorder_detail.pieces or 0)
                    and workorder_detail.planning_pieces <= max_allowed_pcs
                ):
                    workorder_detail.is_palnning = True
                    workorder_detail.status = "In-Planning"
                else:
                    workorder_detail.is_palnning = False

                workorder_detail.save()

                # Process tracking: item + planning-no checklist (even for single/partial plan)
                from workorder.process_tracking import advance_process

                advance_process(
                    workorder_detail=workorder_detail,
                    planning=planning_instance,
                    stage="IN_PLANNING",
                    user=request.user,
                    remarks=f"Planning {planning_instance.planning_no}",
                    sync_legacy_detail_status=False,
                )

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="CREATE",
                    module_name="Planning",
                    description=f"Created planning {planning_instance.planning_no}",
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

        except Exception as e:
            return custom_exception(e)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        data = request.data.copy()
        data["updated_at"] = timezone.now()

        try:
            instance = self.get_object()
            workorder_detail = instance.workorder_detail

            if not workorder_detail:
                return Response(
                    {
                        "success": False,
                        "message": "Workorder detail not found for this planning.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_plan_qty = Decimal(str(data.get("plan_qty", instance.plan_qty or "0")))
            new_plan_pcs = int(data.get("plan_pcs", instance.plan_pcs or 0))

            old_plan_qty = Decimal(str(instance.plan_qty or "0"))
            old_plan_pcs = int(instance.plan_pcs or 0)

            delta_qty = new_plan_qty - old_plan_qty
            delta_pcs = new_plan_pcs - old_plan_pcs

            net_weight = Decimal(str(workorder_detail.net_weight or 0))
            total_pieces = int(workorder_detail.pieces or 0)
            length = Decimal(str(workorder_detail.length or 0))
            wt_per_meter = Decimal(str(workorder_detail.die_profile.wt_kg_p_mt or 0))
            tolerance = workorder_detail.workorder.tolerance or "+-0%"
            percent = int(tolerance.replace("+-", "").replace("%", ""))
            allowed_weight = net_weight + (net_weight * Decimal(percent) / 100)

            total_planned_weight = Decimal(
                str(
                    Planning.objects.filter(workorder_detail=workorder_detail)
                    .exclude(id=instance.id)
                    .aggregate(Sum("plan_qty"))["plan_qty__sum"]
                    or "0"
                )
            )
            total_planned_pcs = (
                Planning.objects.filter(workorder_detail=workorder_detail)
                .exclude(id=instance.id)
                .aggregate(Sum("plan_pcs"))["plan_pcs__sum"]
                or 0
            )

            max_pieces = (
                allowed_weight / (wt_per_meter * (length / 1000))
                if wt_per_meter and length
                else 0
            )

            if total_planned_weight + new_plan_qty > allowed_weight:
                remaining_weight_allowed = allowed_weight - total_planned_weight
                if remaining_weight_allowed <= 0:
                    return Response(
                        {
                            "success": False,
                            "message": f"Planning not allowed. Already fully planned ({total_planned_weight} kg) as per allowed tolerance ({tolerance}).",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(
                    {
                        "success": False,
                        "message": f"Cannot update planning. Already planned: {total_planned_weight} kg. You can only plan {round(remaining_weight_allowed, 2)} kg more as per tolerance ({tolerance}).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if total_planned_pcs + new_plan_pcs > max_pieces:
                remaining_pcs_allowed = int(max_pieces - total_planned_pcs)
                if remaining_pcs_allowed <= 0:
                    return Response(
                        {
                            "success": False,
                            "message": f"Planning not allowed. Already fully planned ({total_planned_pcs} pcs) as per allowed tolerance ({tolerance}).",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(
                    {
                        "success": False,
                        "message": f"Cannot update planning. Already planned: {total_planned_pcs} pcs. You can only plan {remaining_pcs_allowed} pcs more as per tolerance ({tolerance}).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = self.get_serializer(instance, data=data, partial=True)
            if serializer.is_valid():
                planning_instance = serializer.save(updated_by=request.user)

                if (
                    instance.status == "Draft"
                    and planning_instance.die_requisition_detail is not None
                ):
                    planning_instance.status = "Submitted"
                    planning_instance.submitted_by = request.user
                    planning_instance.submitted_at = timezone.now()
                    planning_instance.save(
                        update_fields=["status", "submitted_by", "submitted_at"]
                    )

                workorder_detail.palnning_weight = (
                    workorder_detail.palnning_weight or Decimal("0")
                ) + delta_qty
                workorder_detail.planning_pieces = (
                    workorder_detail.planning_pieces or 0
                ) + delta_pcs

                tolerance_multiplier = 1 + (Decimal(percent) / 100)
                max_allowed_weight = net_weight * tolerance_multiplier
                max_allowed_pcs = total_pieces * tolerance_multiplier

                if (
                    workorder_detail.palnning_weight >= net_weight
                    and workorder_detail.palnning_weight <= max_allowed_weight
                    and workorder_detail.planning_pieces >= total_pieces
                    and workorder_detail.planning_pieces <= max_allowed_pcs
                ):
                    workorder_detail.is_palnning = True
                else:
                    workorder_detail.is_palnning = False

                workorder_detail.save(
                    update_fields=["palnning_weight", "planning_pieces", "is_palnning"]
                )

                payload = clean_payload(request.data)

                log_user_activity(
                    user=request.user,
                    action="UPDATE",
                    module_name="Planning",
                    description=f"Updated planning {planning_instance.planning_no}",
                    request=request,
                    payload=payload,
                )

                return Response(
                    {"success": True, "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )

            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return custom_exception(e)

    @action(detail=True, methods=["patch"], url_path="update-status")
    def update_status(self, request, pk=None):

        planning = get_object_or_404(Planning, pk=pk)

        serializer = PlanningStatusUpdateSerializer(
            planning, data=request.data, partial=True, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Planning status updated successfully",
                "data": PlanningSerializers(planning).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="today")
    def today_planning(self, request):
        """
        Get all planning records which are not fully produced.

        Planning remains in the result until:
            produced_pcs >= plan_pcs

        Optional:
            ?press_id=<press_id>
        """

        try:
            queryset = (
                self.get_queryset()
                .annotate(
                    produced_pcs=Coalesce(
                        Sum(
                            "production_planning__actual_pieces",
                            filter=Q(
                                production_planning__deleted=False
                            ),
                        ),
                        Value(0),
                        output_field=IntegerField(),
                    )
                )
                .annotate(
                    remaining_pcs=F("plan_pcs") - F("produced_pcs")
                )
                .filter(
                    remaining_pcs__gt=0
                )
            )

            # -----------------------------------------
            # OPTIONAL PRESS FILTER
            # -----------------------------------------

            press_id = request.query_params.get("press_id")

            if press_id:
                queryset = queryset.filter(
                    die_requisition_detail__press_id=press_id
                )

            # -----------------------------------------
            # ORDER
            # -----------------------------------------

            queryset = queryset.order_by(
                "die_requisition_detail__press_id",
                "planning_date",
                "id",
            )

            # -----------------------------------------
            # SERIALIZER
            # -----------------------------------------

            serializer = PlanningListSerializer(
                queryset,
                many=True,
                context={"request": request},
            )

            return Response(
                {
                    "success": True,
                    "press_id": press_id,
                    "count": queryset.count(),
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return custom_exception(e)

class ApprovedPlanningViewSet(PlanningViewSet):
    fy_filtering_enabled = False

    def get_queryset(self):
        return super().get_queryset().filter(status__iexact="Approved")
