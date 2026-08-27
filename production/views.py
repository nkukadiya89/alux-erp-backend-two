from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware, now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.master_views import BaseModelViewSet
from common.models import ArchiveMixin
from production.filters import ProductionFilter
from production.models import Production
from production.serializers import (
    ProductionSerializer,
    ProductionShiftSummarySerializer,
    ShiftIdleLogSerializer,
    ShiftUsedLogSerializer,
)
from shift_logs.models import ShiftLog
from utils.generate_number import generate_production_number
from utils.log_activity import clean_payload, log_user_activity
from utils.pagination import Pagination


class ProductionViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = (
        Production.objects.all()
        .select_related(
            "planning",
            "press",
            "workorder",
            "customer",
            "die_profile",
            "die_tool",
            "alloy",
            "temper",
            "shift",
        )
        .prefetch_related("billet_production", "idle_logs", "used_logs", "operators")
        .order_by("-id")
    )
    serializer_class = ProductionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductionFilter
    fy_filtering_enabled = False
    pagination_class = Pagination

    ordering_fields = [
        "planning__planning_no",
        "production_no",
        "production_date",
        "press__name",
        "workorder__order_no",
        "customer__customer_name",
        "customer__code",
        "die_profile__die_number",
        "die_tool__tool_number",
        "alloy__alloy_code",
        "temper__temper_code_new",
        "status",
        "created_at",
        "updated_at",
        "approved_at",
    ]

    @action(detail=False, methods=["get"], url_path="shift-log-list")
    def shift_log_list(self, request):
        """
        Production Shift Log list: one row per production_id with
        summed Maintenance/Operation/Shutdown idle hours, running hrs, used logs.
        GET /api/v1/production/shift-log-list/?page=1&pagesize=20&start_date=&end_date=
        """
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                deleted=False,
                idle_logs__isnull=False,
            ).distinct()
        ).order_by("-created_at", "-id")


        page = self.paginate_queryset(queryset)
        serializer = ProductionShiftSummarySerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def _format_duration(self, total_seconds):
        total_seconds = int(total_seconds or 0)
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _build_duration_summary(self, productions):
        """
        Return only today's total cycle time for "Today's Production".
        """
        today = now().date()
        today_productions = Production.objects.filter(
            deleted=False, created_at__date=today, total_cycle__isnull=False
        ).only("total_cycle")

        total = timedelta()
        for prod in today_productions:
            ct = prod.total_cycle
            if ct:
                total += timedelta(hours=ct.hour, minutes=ct.minute, seconds=ct.second)

        total_seconds = int(total.total_seconds())
        return [
            {
                "date": str(today),
                "total_hours": self._format_duration(total_seconds),
                "day_coverage_ratio": f"{round((total_seconds / 86400) * 100, 2)}%",
                "is_today": True,
            }
        ]
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            fields_param = request.query_params.get("fields")
            if fields_param and fields_param.strip():
                requested_fields = [f.strip() for f in fields_param.split(",") if f.strip()]
                valid_fields = []
                for field in requested_fields:
                    try:
                        queryset.values(field)
                        valid_fields.append(field)
                    except Exception:
                        continue

                if valid_fields:
                    # Keep model-instance queryset for duration summary before converting to values
                    instance_qs = queryset
                    values_qs = queryset.values(*valid_fields)
                    page = self.paginate_queryset(values_qs)
                    if page is not None:
                        return self.get_paginated_response(
                            {
                                "success": True,
                                "data": list(page),
                                "production_duration_summary": self._build_duration_summary(instance_qs),
                            }
                        )
                    return Response(
                        {
                            "success": True,
                            "data": list(values_qs),
                            "production_duration_summary": self._build_duration_summary(instance_qs),
                        },
                        status=status.HTTP_200_OK,
                    )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "data": serializer.data,
                        "production_duration_summary": self._build_duration_summary(queryset),
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "production_duration_summary": self._build_duration_summary(queryset),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["production_no"] = generate_production_number()
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            instance = serializer.save(created_by=request.user)
            log_user_activity(
                user=request.user,
                action="CREATE",
                module_name="Production",
                description=f"Created production {instance.production_no}",
                request=request,
                payload=clean_payload(request.data),
            )
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"], url_path="idle-used-logs")
    def idle_used_logs(self, request, pk=None):
        """
        Return idle_logs + used_logs for a production_id.
        GET /api/v1/production/{id}/idle-used-logs/
        """
        production = self.get_object()
        idle_qs = production.idle_logs.all().order_by("id")
        used_qs = production.used_logs.all().order_by("id")

        return Response(
            {
                "success": True,
                "data": {
                    "production_id": production.id,
                    "production_no": production.production_no,
                    "idle_logs": ShiftIdleLogSerializer(idle_qs, many=True).data,
                    "used_logs": ShiftUsedLogSerializer(used_qs, many=True).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="today-production-report")
    def today_production_report(self, request):
        today = now().date()

        productions = (
            Production.objects.filter(deleted=False, production_date=today)
            .select_related(
                "planning",
                "planning__die_requisition_detail",
                "planning__die_requisition_detail__die_tool",
                "planning__workorder_detail",
                "planning__workorder_detail__die_profile",
                "press",
                "workorder",
                "customer",
                "die_profile",
                "die_tool",
                "alloy",
                "temper",
                "shift",
            )
            .prefetch_related("billet_production", "idle_logs", "used_logs", "operators", "supervisors")
        )

        shift_logs = (
            ShiftLog.objects.filter(deleted=False, created_at__date=today)
            .select_related("press", "shift")
        )

        shift_dict = {}

        for prod in productions:
            shift_name = prod.shift_name_snapshot or (
                prod.shift.shift_name if prod.shift else "Unknown"
            )

            if shift_name not in shift_dict:
                shift_dict[shift_name] = {
                    "shift": shift_name,
                    "press": str(prod.press) if prod.press else None,
                    "production": [],
                    "shift_log": [],
                    "summary": {
                        "idle_type_summary": {},
                        # Shift header fields (Excel PRODUCTION REPORT)
                        "container_temp": None,
                        "oil_temp": None,
                        "die_oven_temp": None,
                        "total_no_of_billets": 0,
                        "maintenance_hours": "00:00",
                        "operation_hours": "00:00",
                        "shutdown_hours": "00:00",
                        "total_input_gross_kg": 0,
                        "total_input_kg_hour": 0,
                        "total_output_gross_kg": 0,
                        "total_output_kg_hour": 0,
                        "recovery": None,
                        "total_running_hours": "00:00",
                        "total_running_minutes": 0,
                        "scrap_weight": 0,
                        "clean_out_used": None,
                        "clean_out_metal_weight": None,
                        "butt_weight": None,
                        "discard_weight": None,
                        "_operators_map": {},
                        "_supervisors_map": {},
                    },
                }

            planning = prod.planning
            die_profile = prod.die_profile
            die_tool = prod.die_tool

            tool_number = None
            if die_profile and die_tool:
                tool_number = ( 
                    f"{die_profile.die_number}-"
                    f"{die_tool.tool_number}"
                )
                if die_tool.die_oblique_number:
                   tool_number += f"/{die_tool.die_oblique_number}"
            elif (
                die_profile
                and planning
                and getattr(planning, "die_requisition_detail", None)
                and getattr(planning.die_requisition_detail, "die_tool", None)
            ):
                tool_number = (
                    f"{die_profile.die_number}-"
                    f"{planning.die_requisition_detail.die_tool.tool_number}"
                )
                if planning.die_requisition_detail.die_tool.die_oblique_number:
                   tool_number += f"/{planning.die_requisition_detail.die_tool.die_oblique_number}"

            section_no = None
            if die_profile:
                section_no = die_profile.die_number
            elif planning and getattr(planning, "workorder_detail", None):
                section_no = getattr(
                    getattr(planning.workorder_detail, "die_profile", None),
                    "die_number",
                    None,
                )

            billet_entries = []
            total_extrude_billets = 0
            input_gross_kg = 0
            for b in prod.billet_production.all():
                extrude = float(b.extrude_billet or 0)
                weight = float(b.billet_weight or 0)
                line_input = round(extrude * weight, 3)
                total_extrude_billets += extrude
                input_gross_kg += line_input
                billet_entries.append(
                    {
                        "billet_size": b.billet_size,
                        "billet_weight": b.billet_weight,
                        "billet_nos": getattr(b, "billet_nos", None),
                        "extrude_billet": b.extrude_billet,
                        "cast_no": b.cast_no,
                        "input_gross_kg": line_input,
                    }
                )
            input_gross_kg = round(input_gross_kg, 3)

            idle_logs = list(prod.idle_logs.all())
            used_logs = list(prod.used_logs.all())

            for idle in idle_logs:
                idle_type = getattr(idle, "type", "Unknown")
                minutes = getattr(idle, "minutes", 0) or 0
                summary = shift_dict[shift_name]["summary"]["idle_type_summary"]

                if idle_type not in summary:
                    summary[idle_type] = {
                        "type": idle_type,
                        "total_minutes": 0,
                        "logs": [],
                    }

                summary[idle_type]["total_minutes"] += minutes
                summary[idle_type]["logs"].append(
                    {
                        "production_id": prod.id,
                        "from_time": getattr(idle, "from_time", None),
                        "to_time": getattr(idle, "to_time", None),
                        "duration": minutes,
                    }
                )

            output_weight = (
                float(prod.total_output_weight)
                if prod.total_output_weight is not None
                else None
            )
            # Excel: INPUT GROSS = Σ (billet_weight × extrude_billet)
            input_weight = input_gross_kg if input_gross_kg else None

            # Excel-style recovery from gross input/output when available
            process_recovery = None
            if input_weight and output_weight is not None and input_weight > 0:
                process_recovery = round((output_weight / input_weight) * 100, 2)
            elif prod.production_process_recovery is not None:
                process_recovery = float(prod.production_process_recovery)

            running_minutes = _time_to_minutes(prod.running_time) or _time_to_minutes(
                prod.total_cycle
            )
            # Prefer stored kg/hour; else derive from gross / running hours
            running_hours = running_minutes / 60 if running_minutes else 0
            derived_input_kg_hour = (
                round(input_weight / running_hours, 3)
                if input_weight and running_hours
                else None
            )
            derived_output_kg_hour = (
                round(output_weight / running_hours, 3)
                if output_weight is not None and running_hours
                else None
            )
            input_kg_hour = (
                float(prod.input_kg_per_hour)
                if prod.input_kg_per_hour is not None
                else derived_input_kg_hour
            )
            output_kg_hour = (
                float(prod.output_kg_per_hour)
                if prod.output_kg_per_hour is not None
                else derived_output_kg_hour
            )

            shift_summary = shift_dict[shift_name]["summary"]
            shift_summary["total_no_of_billets"] += total_extrude_billets
            if input_weight is not None:
                shift_summary["total_input_gross_kg"] += input_weight
            if output_weight is not None:
                shift_summary["total_output_gross_kg"] += output_weight
            if prod.input_kg_per_hour is not None:
                shift_summary["total_input_kg_hour"] += float(prod.input_kg_per_hour)
            elif derived_input_kg_hour is not None:
                shift_summary["total_input_kg_hour"] += derived_input_kg_hour
            if prod.output_kg_per_hour is not None:
                shift_summary["total_output_kg_hour"] += float(prod.output_kg_per_hour)
            elif derived_output_kg_hour is not None:
                shift_summary["total_output_kg_hour"] += derived_output_kg_hour
            shift_summary["total_running_minutes"] += running_minutes
            if prod.scrap is not None:
                shift_summary["scrap_weight"] += float(prod.scrap)

            operators = []
            for op in prod.operators.all():
                full_name = (getattr(op, "full_name", None) or "").strip()
                if not full_name:
                    full_name = f"{op.first_name or ''} {op.last_name or ''}".strip()
                if not full_name:
                    continue
                operators.append({"id": op.id, "full_name": full_name})
                shift_summary["_operators_map"][op.id] = full_name

            supervisors = []
            for sup in prod.supervisors.all():
                full_name = (getattr(sup, "full_name", None) or "").strip()
                if not full_name:
                    full_name = f"{sup.first_name or ''} {sup.last_name or ''}".strip()
                if not full_name:
                    continue
                supervisors.append({"id": sup.id, "full_name": full_name})
                shift_summary["_supervisors_map"][sup.id] = full_name

            shift_dict[shift_name]["production"].append(
                {
                    # ---- existing fields (unchanged keys) ----
                    "production_id": prod.id,
                    "production_no": prod.production_no,
                    "production_date": prod.production_date,
                    "po_no": planning.planning_no if planning else None,
                    "workorder_no": prod.workorder.order_no if prod.workorder else None,
                    "tool_number": tool_number,
                    "section_no": section_no,
                    "cavity": prod.cavity,
                    "alloy": (
                        {
                            "name": prod.alloy.alloy_code,
                            "standard_name": getattr(
                                prod.alloy, "standard_name", None
                            ),
                        }
                        if prod.alloy
                        else None
                    ),
                    "speed": prod.speed,
                    "temper": str(prod.temper) if prod.temper else None,
                    "quenching_type": prod.quenching_type
                    or getattr(planning, "quenching_type", None),
                    "billet_entries": billet_entries,
                    "input_weight": input_weight,
                    "output_weight": output_weight,
                    "cast_no": next(
                        (b.get("cast_no") for b in billet_entries if b.get("cast_no")),
                        None,
                    ),
                    "billet_temp": prod.billet_temp,
                    "die_temp": prod.die_temp,
                    "time_in": prod.time_in,
                    "time_out": prod.time_out,
                    "ext_pressure": prod.ext_pressure,
                    "total_cycle": prod.total_cycle,
                    "recovery": process_recovery,
                    "remark": prod.remarks,
                    "completion_status": prod.completion_status,
                    "deviation_type": prod.deviation_type,
                    "program_break_reason": prod.program_break_reason,
                    "failure_reason": prod.failure_reason,
                    "die_tool_return_status": prod.die_tool_return_status,
                    "operators": operators,
                    "supervisors": supervisors,
                    "idle_logs": [
                        {
                            "type": idle.type,
                            "reason": idle.reason,
                            "from_time": idle.from_time,
                            "to_time": idle.to_time,
                            "duration": idle.minutes,
                        }
                        for idle in idle_logs
                    ],
                    "used_logs": [
                        {
                            "alloy": used.alloy,
                            "log_qty": used.log_qty,
                        }
                        for used in used_logs
                    ],
                    # ---- added Excel report params ----
                    "die_no": die_profile.die_number if die_profile else None,
                    "die_station_no": prod.die_station_no,
                    "cutting_length_mm": prod.cut_length,
                    "billet_size": billet_entries[0]["billet_size"]
                    if billet_entries
                    else None,
                    "billet_weight": billet_entries[0]["billet_weight"]
                    if billet_entries
                    else None,
                    "total_no_of_billet_extrude": round(total_extrude_billets, 3),
                    "weight_per_meter": prod.weight_per_meter,
                    "weight_per_piece": prod.weight_per_piece,
                    "input_kg_per_hour": input_kg_hour,
                    "output_kg_per_hour": output_kg_hour,
                    "target_speed": prod.speed,
                    "max_speed": None,
                    "planning_pieces": prod.pieces,
                    "actual_good_cutting_pieces": prod.actual_pieces,
                    "total_output_weight": prod.total_output_weight,
                    "planning_process_recovery": prod.planning_recovery,
                    "production_process_recovery": process_recovery
                    if process_recovery is not None
                    else (
                        float(prod.production_process_recovery)
                        if prod.production_process_recovery is not None
                        else None
                    ),
                    "running_time": prod.running_time,
                    "total_hours": prod.running_time or prod.total_cycle,
                    "scrap": prod.scrap,
                }
            )

        for log in shift_logs:
            shift_name = log.shift.shift_name if log.shift else "Unknown"

            if shift_name not in shift_dict:
                shift_dict[shift_name] = {
                    "shift": shift_name,
                    "press": str(log.press) if log.press else None,
                    "production": [],
                    "shift_log": [],
                    "summary": {
                        "idle_type_summary": {},
                        "container_temp": None,
                        "oil_temp": None,
                        "die_oven_temp": None,
                        "total_no_of_billets": 0,
                        "maintenance_hours": "00:00",
                        "operation_hours": "00:00",
                        "shutdown_hours": "00:00",
                        "total_input_gross_kg": 0,
                        "total_input_kg_hour": 0,
                        "total_output_gross_kg": 0,
                        "total_output_kg_hour": 0,
                        "recovery": None,
                        "total_running_hours": "00:00",
                        "total_running_minutes": 0,
                    },
                }

            shift_dict[shift_name]["shift_log"].append(
                {
                    "shift_log_id": log.id,
                    "press": str(log.press) if log.press else None,
                    "shift": str(log.shift) if log.shift else None,
                    "start_time": getattr(log.shift, "start_time", None)
                    if log.shift
                    else None,
                    "end_time": getattr(log.shift, "end_time", None)
                    if log.shift
                    else None,
                }
            )

        for shift in shift_dict.values():
            summary = shift["summary"]
            idle_summary = summary["idle_type_summary"]

            idle_list = []
            for idle_type in ("Maintenance", "Operation", "Shutdown"):
                item = idle_summary.get(idle_type) or {
                    "type": idle_type,
                    "total_minutes": 0,
                    "logs": [],
                }
                total_time = _format_minutes(item["total_minutes"])
                idle_list.append(
                    {
                        "type": item["type"],
                        "total_minutes": item["total_minutes"],
                        "total_time": total_time,
                        "logs": item["logs"],
                    }
                )
                if idle_type == "Maintenance":
                    summary["maintenance_hours"] = total_time
                elif idle_type == "Operation":
                    summary["operation_hours"] = total_time
                elif idle_type == "Shutdown":
                    summary["shutdown_hours"] = total_time

            # Include any unexpected idle types
            for key, item in idle_summary.items():
                if key not in ("Maintenance", "Operation", "Shutdown"):
                    idle_list.append(
                        {
                            "type": item["type"],
                            "total_minutes": item["total_minutes"],
                            "total_time": _format_minutes(item["total_minutes"]),
                            "logs": item["logs"],
                        }
                    )

            summary["idle_type_summary"] = idle_list
            summary["total_no_of_billets"] = round(summary["total_no_of_billets"], 3)
            summary["total_input_gross_kg"] = round(
                summary["total_input_gross_kg"], 3
            )
            summary["total_output_gross_kg"] = round(
                summary["total_output_gross_kg"], 3
            )
            summary["total_input_kg_hour"] = round(summary["total_input_kg_hour"], 3)
            summary["total_output_kg_hour"] = round(
                summary["total_output_kg_hour"], 3
            )
            summary["total_running_hours"] = _format_minutes(
                summary.pop("total_running_minutes", 0)
            )
            summary["scrap_weight"] = round(summary.get("scrap_weight") or 0, 3)
            operators_map = summary.pop("_operators_map", {}) or {}
            summary["operators"] = [
                {"id": op_id, "full_name": name}
                for op_id, name in operators_map.items()
            ]
            supervisors_map = summary.pop("_supervisors_map", {}) or {}
            summary["supervisors"] = [
                {"id": sup_id, "full_name": name}
                for sup_id, name in supervisors_map.items()
            ]

            in_kg = summary["total_input_gross_kg"]
            out_kg = summary["total_output_gross_kg"]
            summary["recovery"] = (
                round((out_kg / in_kg) * 100, 2) if in_kg else None
            )

        payload = {
            "date": today.strftime("%d-%m-%Y"),
            "has_data": bool(shift_dict),
            "shifts": shift_dict,
        }
        message = (
            "No production entries found for today."
            if not shift_dict
            else "Today production report fetched successfully."
        )

        return Response(
            {
                "success": True,
                "message": message,
                "data": payload,
            }
        )


def _format_minutes(total_minutes):
    if not total_minutes:
        return "00:00"
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02}:{minutes:02}"


def _time_to_minutes(value):
    if not value:
        return 0
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, timedelta):
        return int(value.total_seconds() // 60)
    if isinstance(value, str):
        parts = value.split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return h * 60 + m
        except (TypeError, ValueError):
            return 0
    return 0
