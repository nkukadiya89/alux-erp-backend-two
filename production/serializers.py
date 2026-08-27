from rest_framework import serializers
from common.serializers import BaseModelSerializer
from django.db.models import Q
from customer.models import Customer
from die.models import Die, DiePress, DieTool
from dietool_production.models import DieTrialLog
from die_requisition.models import DieRequisition
from die.serializers import DieToolSerializers
from die_requisition.serializers import DieRequisitionSerializer
from planning.models import Planning
from product.models import Alloy, Temper
from product.sort_serializers import AlloySortSerializers, TemperSortSerializers
from production.models import BilletMaster, Production, ShiftIdleLog, ShiftUsedLog
from shift.models import ShiftMaster
from shift.serializers import ShiftMasterSerializer
from shift_logs.serializers import ShiftLogSerializer
from user.models import User
from user.serializers import UserQuickSerializer
from workorder.models import WorkOrder
from utils.generate_number import generate_trial_no


def _minutes_to_hms(minutes):
    minutes = int(minutes or 0)
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


def _time_to_minutes(value):
    if not value:
        return 0
    return value.hour * 60 + value.minute

class DiePressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiePress
        fields = ["id", "name", "billet_wt_factor", "billet_length_min", "billet_length_max", "billet_wt_factor"]

class WorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["id", "order_no", "purchase_order_no", "purchase_order_date", "order_date"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "code", "customer_name"]


class DieSerializer(serializers.ModelSerializer):
    ballon_drawing_dimensions = serializers.SerializerMethodField()

    class Meta:
        model = Die
        fields = ["id", "die_number", "ballon_drawing_dimensions"]

    def get_ballon_drawing_dimensions(self, obj):
        from die.models import SectionBallonDimensions

        return list(
            SectionBallonDimensions.objects.filter(section=obj, deleted=False).values(
                "id", "balloon_no", "dim_type", "nominal_value", "tolerance_plus",
                "tolerance_minus", "min_value", "max_value", "description",
                "is_inspection", "is_critical",
            )
        )


class PlanningSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planning
        fields = ["id", "planning_no", "quenching_type"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["die_requisition"] = (
            DieRequisitionSerializer(instance.die_requisition).data
            if instance.die_requisition
            else None
        )
        return ret


class BilletMasterSerializer(serializers.ModelSerializer):
    input_gross_kg = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BilletMaster
        fields = [
            "id",
            "billet_size",
            "billet_weight",
            "extrude_billet",
            "cast_no",
            "input_gross_kg",
        ]

    def get_input_gross_kg(self, obj):
        try:
            return round(float(obj.billet_weight or 0) * float(obj.extrude_billet or 0), 3)
        except (TypeError, ValueError):
            return 0


class ShiftIdleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftIdleLog
        fields = ["id", "type", "from_time", "to_time", "minutes", "reason"]
        read_only_fields = ["minutes"]


class ShiftUsedLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftUsedLog
        fields = ["id", "alloy", "log_qty"]


class ProductionSerializer(BaseModelSerializer):
    press = serializers.PrimaryKeyRelatedField(queryset=DiePress.objects.all())
    workorder = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all())
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    die_profile = serializers.PrimaryKeyRelatedField(queryset=Die.objects.all())
    die_tool = serializers.PrimaryKeyRelatedField(
        queryset=DieTool.objects.all(), required=False, allow_null=True
    )
    operators = serializers.PrimaryKeyRelatedField(
        queryset = User.objects.all(), many=True, required=False
    )
    operators_detail = UserQuickSerializer(source="operators", many=True, read_only=True)
    supervisors = serializers.PrimaryKeyRelatedField(
        queryset = User.objects.all(), many=True, required=False
    )
    supervisors_detail = UserQuickSerializer(source="supervisors", many=True, read_only=True)
    alloy = serializers.PrimaryKeyRelatedField(queryset=Alloy.objects.all())
    temper = serializers.PrimaryKeyRelatedField(
        queryset=Temper.objects.all(), required=False, allow_null=True
    )
    planning = serializers.PrimaryKeyRelatedField(
        queryset=Planning.objects.all(), required=False, allow_null=True
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=ShiftMaster.objects.filter(is_active=True), required=False, allow_null=True
    )
    billet_details = BilletMasterSerializer(
        source="billet_production", many=True, required=False, read_only=False
    )
    idle_logs = ShiftIdleLogSerializer(many=True, required=False, read_only=False)
    used_logs = ShiftUsedLogSerializer(many=True, required=False, read_only=False)

    shift_details = serializers.SerializerMethodField(read_only=True)
    input_gross_qty = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Production
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "planning",
            "production_date",
            "production_no",
            "press",
            "workorder",
            "customer",
            "die_profile",
            "die_tool",
            "alloy",
            "cavity",
            "temper",
            "quenching_type",
            "operators",
            "operators_detail",
            "supervisors",
            "supervisors_detail",
            "status",
            "completion_status",
            "deviation_type",
            "program_break_reason",
            "failure_reason",
            "billet_temp",
            "die_temp",
            "die_station_no",
            "operators",
            "time_in",
            "time_out",
            "total_cycle",
            "running_time",
            "cut_length",
            "pieces",
            "actual_pieces",
            "weight_per_piece",
            "scrap",
            "speed",
            "input_kg_per_hour",
            "output_kg_per_hour",
            "weight_per_meter",
            "total_output_weight",
            "planning_recovery",
            "production_process_recovery",
            "ext_pressure",
            "remarks",
            "shift",
            "shift_details",
            "billet_details",
            "die_tool_return_status",
            "idle_logs",
            "used_logs",
            "input_gross_qty",
        ]
        read_only_fields = [
            "shift_name_snapshot",
            "shift_start_snapshot",
            "shift_end_snapshot",
            "input_gross_qty",
        ]

    def get_input_gross_qty(self, obj):
        """Not stored — Σ (billet_weight × extrude_billet) from billet_details."""
        total = 0.0
        for billet in obj.billet_production.all():
            try:
                total += float(billet.billet_weight or 0) * float(
                    billet.extrude_billet or 0
                )
            except (TypeError, ValueError):
                continue
        return round(total, 3)

    def get_shift_details(self, obj):
        if obj.shift_name_snapshot:
            return {
                "id": obj.shift_id,
                "name": obj.shift_name_snapshot,
                "start_time": obj.shift_start_snapshot,
                "end_time": obj.shift_end_snapshot,
            }
        return None

    def _update_die_tool_running_kg(self, production, old_output_weight=0):
        if not production.die_tool:
           return

        current_output_weight = float(production.total_output_weight or 0)
        old_output_weight = float(old_output_weight or 0)

        die_tool = production.die_tool

        current_running_kg = float(die_tool.total_running_kg or 0)

        new_running_kg = (
            current_running_kg
            - old_output_weight
            + current_output_weight
        )

        die_tool.total_running_kg = max(new_running_kg, 0)

        die_tool.save(
            update_fields=["total_running_kg"]
        )    

    def _sync_die_trial_entry(self, production):
        """
        Create / update Die Tool Trial Management entry
        only when Production belongs to a Trial Work Order.
        """

        # ---------------------------------------------
        # Step 1: Work Order check
        # ---------------------------------------------
        workorder = production.workorder

        if not workorder:
            return None

        if workorder.order_type != "trial":
            return None

        # ---------------------------------------------
        # Step 2: Die Tool is compulsory for Trial
        # ---------------------------------------------
        if not production.die_tool:
            return None

        # ---------------------------------------------
        # Step 3: Check existing Trial for this Production
        # ---------------------------------------------
        trial = DieTrialLog.objects.filter(
            production=production
        ).first()

        # ---------------------------------------------
        # Step 4: Get billet size
        # ---------------------------------------------
        billet = (
            production.billet_production
            .order_by("id")
            .first()
        )

        billet_size = (
            billet.billet_size
            if billet
            else None
        )

        # ---------------------------------------------
        # Step 5: CREATE
        # ---------------------------------------------
        if not trial:

            previous_trial_count = DieTrialLog.objects.filter(
                die_tool=production.die_tool
            ).count()

            if previous_trial_count == 0:
                trial_type = "new"
            else:
                trial_type = "repeat"

            trial = DieTrialLog.objects.create(
                trial_no=generate_trial_no(),
                die_tool=production.die_tool,
                production=production,
                trial_date=production.production_date,
                trial_type=trial_type,
                alloy=production.alloy,
                temper=production.temper,
                billet_size=billet_size,
                total_extrude_kg=production.total_output_weight,
                trial_count=previous_trial_count + 1,
                remarks=production.remarks,
            )

        # ---------------------------------------------
        # Step 6: UPDATE existing Trial
        # ---------------------------------------------
        else:
            trial.trial_date = production.production_date
            trial.die_tool = production.die_tool
            trial.alloy = production.alloy
            trial.temper = production.temper
            trial.billet_size = billet_size
            trial.total_extrude_kg = production.total_output_weight
            trial.remarks = production.remarks

            # IMPORTANT:
            # Don't change trial_type / trial_count
            # during normal Production update.

            trial.save()

        # ---------------------------------------------
        # Step 7: Shift Snapshot
        # ---------------------------------------------
        if production.shift:
            trial.capture_shift_snapshot(
                production.shift
            )
            trial.save()

        return trial

    def _close_die_requisition_if_complete(self, production):
        """
        Automatically close Die Requisition when
        Production is completed.
        """

        # Step 1: Production must be complete
        if production.completion_status != "ORDER_COMPLETE":
            return

        # Step 2: WorkOrder is required
        if not production.workorder:
            return

        # Step 3: Find active Die Requisition
        requisitions = DieRequisition.objects.filter(
            workorder_no=production.workorder,
            deleted=False,
        ).exclude(
            status__in=["Closed", "Rejected"]
        )

        # Step 4: Close requisitions
        requisitions.update(
            status="Closed"
        )
    def validate_shift(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Selected shift is inactive.")
        return value
    
    def _sync_nested(self, queryset, model, parent_field, parent_instance, data_list):
        if data_list is None:
            return

        existing_ids = []

        for data in data_list:

            row_id = data.pop("id", None)

            if row_id:
                obj = queryset.filter(id=row_id).first()

                if obj:
                    for key, value in data.items():
                        setattr(obj, key, value)

                    obj.save()
                    existing_ids.append(obj.id)
                    continue

            obj = model.objects.create(
                **{
                    parent_field: parent_instance,
                    **data,
                }
            )

            existing_ids.append(obj.id)

        queryset.exclude(id__in=existing_ids).delete()

    def validate(self, attrs):
        time_in = attrs.get("time_in", getattr(self.instance, "time_in", None))
        time_out = attrs.get("time_out", getattr(self.instance, "time_out", None))
        production_date = attrs.get("production_date", getattr(self.instance, "production_date", None))
        press = attrs.get("press", getattr(self.instance, "press", None))
        if time_in and time_out and time_out <= time_in:
            raise serializers.ValidationError(
                {"time_out": "Stop Time must be after Start Time."}
            )

        # ---------------------------------------------------------
        # 2. Prevent Production Time Overlap
        #    Same Date + Same Press
        # ---------------------------------------------------------
        if production_date and press and time_in and time_out:

            overlapping_qs = Production.objects.filter(
                deleted=False,
                production_date=production_date,
                press=press,
                time_in__lt=time_out,
                time_out__gt=time_in,
            )

            if self.instance:
                overlapping_qs = overlapping_qs.exclude(
                    id=self.instance.id
                )

            if overlapping_qs.exists():
                overlapping_production = overlapping_qs.first()

                raise serializers.ValidationError({
                    "time_in": (
                        f"Production time overlaps with "
                        f"{overlapping_production.production_no} "
                        f"({overlapping_production.time_in.strftime('%I:%M %p')} - "
                        f"{overlapping_production.time_out.strftime('%I:%M %p')})."
                    ),
                    "time_out": "Please select a non-overlapping time."
                })

        entry_status = attrs.get(
            "status",
            getattr(self.instance, "status", Production.STATUS_SUBMITTED)
            if self.instance
            else attrs.get("status", Production.STATUS_SUBMITTED),
        )
        if entry_status is None:
            entry_status = Production.STATUS_SUBMITTED

        # Draft: identity / start fields only. Final submit: full output + completion.
        if entry_status == Production.STATUS_DRAFT:
            draft_required = {
                "planning": "Billet Planning is required for draft.",
                "production_date": "Production date is required for draft.",
                "workorder": "Work Order is required for draft.",
                "press": "Press is required for draft.",
                "shift": "Shift is required for draft.",
                "customer": "Customer is required for draft.",
                "die_profile": "Section Number is required for draft.",
                "die_tool": "Die Tool is required for draft.",
                "quenching_type": "Quenching Type is required for draft.",
                "die_station_no": "Die Station No. is required for draft.",
                "time_in": "Start Time is required for draft.",
            }
            errors = {}
            for field, message in draft_required.items():
                value = attrs.get(
                    field,
                    getattr(self.instance, field, None) if self.instance else None,
                )
                if value in (None, ""):
                    errors[field] = message
            if errors:
                raise serializers.ValidationError(errors)
            return attrs

        # SUBMITTED — start fields + fields only known when production completes
        final_required = {
            "planning": "Billet Planning is required for final submit.",
            "production_date": "Production date is required for final submit.",
            "workorder": "Work Order is required for final submit.",
            "press": "Press is required for final submit.",
            "shift": "Shift is required for final submit.",
            "customer": "Customer is required for final submit.",
            "die_profile": "Section Number is required for final submit.",
            "die_tool": "Die Tool is required for final submit.",
            "quenching_type": "Quenching Type is required for final submit.",
            "die_station_no": "Die Station No. is required for final submit.",
            "time_in": "Start Time is required for final submit.",
            "time_out": "Stop Time is required for final submit.",
            "total_cycle": "Gross Cycle Time is required for final submit.",
            "ext_pressure": "Extrusion Pressure is required for final submit.",
            "billet_temp": "Billet Temp is required for final submit.",
            "die_temp": "Die Temp is required for final submit.",
            "weight_per_meter": "Weight / Meter is required for final submit.",
            "pieces": "Planning Pieces is required for final submit.",
            "actual_pieces": "Actual Good Cutting Pieces is required for final submit.",
            "weight_per_piece": "Weight / Piece is required for final submit.",
            "completion_status": "Completion Status is required for final submit.",
            "die_tool_return_status": "Die Tool Return Status is required for final submit.",
        }
        errors = {}
        for field, message in final_required.items():
            value = attrs.get(
                field,
                getattr(self.instance, field, None) if self.instance else None,
            )
            if value in (None, ""):
                errors[field] = message
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        shift = validated_data.pop("shift", None)
        operators = validated_data.pop("operators", [])
        supervisors = validated_data.pop("supervisors", [])
        billet_details = validated_data.pop("billet_production", None)
        idle_logs = validated_data.pop("idle_logs", None)
        used_logs = validated_data.pop("used_logs", None)

        production = Production(**validated_data)
        if shift:
            production.capture_shift_snapshot(shift)
        production.save()

        if production.status == Production.STATUS_SUBMITTED:
            self._update_die_tool_running_kg(production, old_output_weight=0)

        production.operators.set(operators)
        production.supervisors.set(supervisors)
        self._sync_nested(production.billet_production.all(), BilletMaster, "production", production, billet_details)
        self._sync_nested(production.idle_logs.all(), ShiftIdleLog, "production", production, idle_logs)
        self._sync_nested(production.used_logs.all(), ShiftUsedLog, "production", production, used_logs)

        if production.status == Production.STATUS_SUBMITTED:
            self._sync_die_trial_entry(production)
            self._close_die_requisition_if_complete(production)

        if production.planning and production.planning.status not in ("In-Progress", "Completed"):
            production.planning.status = "In-Progress"
            production.planning.save(update_fields=["status"])

        if production.status == Production.STATUS_SUBMITTED:
            self._advance_process_tracking(production)

        return production

    def update(self, instance, validated_data):
        previous_status = instance.status
        old_output_weight = instance.total_output_weight
        shift = validated_data.pop("shift", None)
        operators = validated_data.pop("operators", None)
        supervisors = validated_data.pop("supervisors", None)
        billet_details = validated_data.pop("billet_production", None)
        idle_logs = validated_data.pop("idle_logs", None)
        used_logs = validated_data.pop("used_logs", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if shift:
            instance.capture_shift_snapshot(shift)

        instance.save()

        if operators is not None:
           instance.operators.set(operators)

        if supervisors is not None:
            instance.supervisors.set(supervisors)

        self._sync_nested(instance.billet_production.all(), BilletMaster,"production", instance, billet_details)
        self._sync_nested(instance.idle_logs.all(), ShiftIdleLog, "production", instance, idle_logs)
        self._sync_nested(instance.used_logs.all(), ShiftUsedLog, "production", instance, used_logs)

        if instance.status == Production.STATUS_SUBMITTED:
            # Apply die-tool kg when first finalizing a draft, or when already submitted.
            baseline = (
                0
                if previous_status == Production.STATUS_DRAFT
                else old_output_weight
            )
            self._update_die_tool_running_kg(instance, old_output_weight=baseline)
            self._sync_die_trial_entry(instance)
            self._close_die_requisition_if_complete(instance)

        if instance.planning and instance.planning.status not in ("In-Progress", "Completed"):
            instance.planning.status = "In-Progress"
            instance.planning.save(update_fields=["status"])

        if instance.status == Production.STATUS_SUBMITTED:
            self._advance_process_tracking(instance)

        return instance

    def _advance_process_tracking(self, production):
        try:
            from workorder.process_tracking import advance_process

            planning = production.planning
            detail = planning.workorder_detail if planning else None
            if not detail:
                return
            advance_process(
                workorder_detail=detail,
                planning=planning,
                stage="IN_PRODUCTION",
                user=self.context.get("request").user
                if self.context.get("request")
                else None,
                remarks=f"Production {production.production_no}",
            )
        except Exception:
            # Never break production save due to tracking
            pass

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["planning"] = PlanningSerializer(instance.planning).data if instance.planning else None
        rep["press"] = DiePressSerializer(instance.press).data if instance.press else None
        rep["workorder"] = WorkOrderSerializer(instance.workorder).data if instance.workorder else None
        rep["customer"] = CustomerSerializer(instance.customer).data if instance.customer else None
        rep["die_profile"] = DieSerializer(instance.die_profile).data if instance.die_profile else None
        rep["die_tool"] = DieToolSerializers(instance.die_tool).data if instance.die_tool else None
        rep["alloy"] = AlloySortSerializers(instance.alloy).data if instance.alloy else None
        rep["temper"] = TemperSortSerializers(instance.temper).data if instance.temper else None
        rep["billet_details"] = BilletMasterSerializer(instance.billet_production.all(), many=True).data
        rep["idle_logs"] = ShiftIdleLogSerializer(instance.idle_logs.all(), many=True).data
        rep["used_logs"] = ShiftUsedLogSerializer(instance.used_logs.all(), many=True).data
        return rep


class ProductionShiftReportSerializer(serializers.Serializer):
    shift = ShiftMasterSerializer()
    productions = serializers.SerializerMethodField()
    shift_logs = serializers.SerializerMethodField()

    def get_productions(self, obj):
        return ProductionSerializer(obj["productions"], many=True).data

    def get_shift_logs(self, obj):
        return ShiftLogSerializer(obj["shift_logs"], many=True).data


class ProductionShiftSummarySerializer(serializers.ModelSerializer):
    """
    One row per production_id with summed idle hours / used logs
    for the Production Shift Log list screen.
    """

    production_id = serializers.IntegerField(source="id", read_only=True)
    date = serializers.SerializerMethodField()
    press = DiePressSerializer(read_only=True)
    shift_details = serializers.SerializerMethodField()
    idle_summary = serializers.SerializerMethodField()
    total_idle_hrs = serializers.SerializerMethodField()
    total_running_hrs = serializers.SerializerMethodField()
    total_log_qty = serializers.SerializerMethodField()
    operators = UserQuickSerializer(many=True, read_only=True)
    supervisors = UserQuickSerializer(many=True, read_only=True)

    class Meta:
        model = Production
        fields = [
            "id",
            "production_id",
            "production_no",
            "date",
            "shift",
            "shift_details",
            "press",
            "operators",
            "supervisors",
            "idle_summary",
            "total_idle_hrs",
            "total_running_hrs",
            "total_log_qty",
            "created_at",
        ]

    def get_date(self, obj):
        if obj.created_at:
            return obj.created_at.date()
        return None

    def get_shift_details(self, obj):
        if obj.shift_name_snapshot:
            return {
                "id": obj.shift_id,
                "name": obj.shift_name_snapshot,
                "start_time": obj.shift_start_snapshot,
                "end_time": obj.shift_end_snapshot,
            }
        if obj.shift:
            return {
                "id": obj.shift.id,
                "name": obj.shift.shift_name,
                "start_time": obj.shift.start_time,
                "end_time": obj.shift.end_time,
            }
        return None

    def get_idle_summary(self, obj):
        summary = {"Maintenance": "00:00:00", "Operation": "00:00:00", "Shutdown": "00:00:00"}
        totals = {"Maintenance": 0, "Operation": 0, "Shutdown": 0}

        for idle in obj.idle_logs.all():
            idle_type = idle.type
            if idle_type in totals:
                totals[idle_type] += idle.minutes or 0

        for idle_type, minutes in totals.items():
            summary[idle_type] = _minutes_to_hms(minutes)
        return summary

    def get_total_idle_hrs(self, obj):
        total_minutes = sum((idle.minutes or 0) for idle in obj.idle_logs.all())
        return _minutes_to_hms(total_minutes)

    def get_total_log_qty(self, obj):
        return sum((used.log_qty or 0) for used in obj.used_logs.all())

    def get_total_running_hrs(self, obj):
        if obj.running_time:
            return (
                f"{obj.running_time.hour:02d}:"
                f"{obj.running_time.minute:02d}:"
                f"{obj.running_time.second:02d}"
            )

        idle_total = sum((idle.minutes or 0) for idle in obj.idle_logs.all())

        if obj.shift and getattr(obj.shift, "duration_minutes", None):
            return _minutes_to_hms(max(obj.shift.duration_minutes - idle_total, 0))

        if obj.time_in and obj.time_out:
            cycle = max(_time_to_minutes(obj.time_out) - _time_to_minutes(obj.time_in), 0)
            return _minutes_to_hms(max(cycle - idle_total, 0))

        return "00:00:00"