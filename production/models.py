from django.db import models
from customer.models import Customer
from die.models import Die, DiePress, DieTool
from planning.models import Planning
from product.models import Alloy, Temper
from settings.models import BaseModule
from workorder.models import WorkOrder
from shift.models import ShiftSnapshotMixin
from django.conf import settings

class Production(ShiftSnapshotMixin, BaseModule):
    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    ENTRY_STATUS = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
    )
    COMPLETION_STATUS = (
        ("ORDER_COMPLETE", "Order Complete"),
        ("ORDER_COMPLETE_WITH_DEVIATION", "Order Complete With Deviation"),
        ("PROGRAM_BREAK", "Program Break"),
        ("DIE_FAIL", "Die Fail"),
        ("HAND_OVER", "Hand Over (Next Shift)"),
    )
    DIETOOL_RETURN_STATUS = (
        ("RETURN_TO_DIE_TOOL_ROOM", "Return to Die Tool Room"),
        ("KEEP_AT_PRESS", "Keep at Press"),
    )
    DEVIATION_TYPE = (
        ("SECTION_CUT", "Section Cut"),
        ("ROUGHNESS", "Roughness"),
        ("JOINT", "Joint"),
        ("DIMENSION", "Dimension"),
        ("OTHER", "Other"),
    )

    PROGRAM_BREAK_REASON = (
        ("DIE_TOOL_MAINTENANCE", "Die Tool Maintenance"),
        ("SHUTDOWN", "Shutdown"),
        ("ALLOY_CHANGE", "Alloy Change"),
        ("POWER_FAILURE", "Power Failure"),
        ("BILLET_FINISH", "Billet Finish"),
        ("OTHER", "Other"),
    )

    FAILURE_REASON = (
        ("ROUGHNESS", "Roughness"),
        ("SECTION_CUT", "Section Cut"),
        ("JOINT_PROBLEM", "Joint Problem"),
        ("DIE_CRACK", "Die Crack"),
        ("DIMENSION", "Dimension"),
        ("OTHER", "Other"),
    )
    planning = models.ForeignKey(
        Planning,
        on_delete=models.CASCADE,
        related_name="production_planning",
        null=True,
    )
    production_no = models.CharField(max_length=100, null=False, blank=False)
    production_date = models.DateField(null=True)
    press = models.ForeignKey(
        DiePress,
        on_delete=models.CASCADE,
        related_name="production_die_press",
        null=True,
    )
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="production_workorder",
        null=True,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="production_of_customer",
        null=True,
    )
    die_profile = models.ForeignKey(
        Die, on_delete=models.CASCADE, related_name="production_die", null=True
    )
    die_tool = models.ForeignKey(
        DieTool, on_delete=models.CASCADE, related_name="production_die_tool", null=True
    )
    cavity = models.IntegerField(default=0)
    alloy = models.ForeignKey(
        Alloy, on_delete=models.CASCADE, related_name="production_alloy", null=True
    )
    temper = models.ForeignKey(
        Temper, on_delete=models.CASCADE, related_name="production_temper", null=True
    )
    quenching_type = models.CharField(max_length=100, null=True, blank=True)
    billet_temp = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Billet temperature in °C",
    )
    die_temp = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Die temperature in °C",
    )
    die_station_no = models.PositiveIntegerField(
        null=True, blank=True, help_text="Die station number"
    )
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    total_cycle = models.TimeField(null=True, blank=True)
    running_time = models.TimeField(null=True, blank=True)
    ext_pressure = models.FloatField(default=0.0, null=True)
    cut_length = models.CharField(max_length=100, null=True, blank=True)
    pieces = models.IntegerField(default=0, null=True)
    actual_pieces = models.IntegerField(default=0, null=True)
    weight_per_piece = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    weight_per_meter = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    total_output_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    planning_recovery = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    production_process_recovery = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    scrap = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    speed = models.CharField(max_length=15, null=True, blank=True) 
    input_kg_per_hour = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    output_kg_per_hour = models.DecimalField(decimal_places=3, max_digits=10, null=True) 
    status = models.CharField(
        max_length=20,
        choices=ENTRY_STATUS,
        default=STATUS_SUBMITTED,
        db_index=True,
        help_text="DRAFT = production started (incomplete output); SUBMITTED = final submit",
    )
    completion_status = models.CharField(
        max_length=50,
        choices=COMPLETION_STATUS,
        null=True,
        blank=True,
    )
    die_tool_return_status = models.CharField(
        max_length=30,
        choices=DIETOOL_RETURN_STATUS,
        default="RETURN_TO_DIE_TOOL_ROOM",
    )
    deviation_type = models.CharField(
        max_length=50,
        choices=DEVIATION_TYPE,
        null=True,
        blank=True,
    )
    program_break_reason = models.CharField(
        max_length=50,
        choices=PROGRAM_BREAK_REASON,
        null=True,
        blank=True,
    )
    failure_reason = models.CharField(
        max_length=50,
        choices=FAILURE_REASON,
        null=True,
        blank=True,
    )
    operators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="production_operators",
        blank=True,
    )
    supervisors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="production_supervisors",
        blank=True,
    )   
    remarks = models.TextField(null=True)
    
    def __str__(self):
        return self.production_no

    class Meta:
        db_table = "production"


class BilletMaster(models.Model):
    production = models.ForeignKey(
        Production,
        on_delete=models.CASCADE,
        related_name="billet_production",
        null=True,
    )
    billet_size = models.CharField(max_length=100, null=True, blank=True)
    billet_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    extrude_billet = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    cast_no = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.billet_size

    class Meta:
        db_table = "billet_master"


class ShiftIdleLog(models.Model):
    IDLE_TYPE = [
        ("Maintenance", "Maintenance"),
        ("Operation", "Operation"),
        ("Shutdown", "Shutdown"),
    ]
    production = models.ForeignKey(
        Production,
        related_name="idle_logs",
        on_delete=models.CASCADE,
        null=True,
    )
    type = models.CharField(max_length=20, choices=IDLE_TYPE)
    from_time = models.TimeField()
    to_time = models.TimeField()
    minutes = models.PositiveIntegerField()
    reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "shift_idle_log"

    def save(self, *args, **kwargs):
        if self.from_time and self.to_time:
            diff = (
                self.to_time.hour * 60
                + self.to_time.minute
                - (self.from_time.hour * 60 + self.from_time.minute)
            )
            self.minutes = max(diff, 0)

        super().save(*args, **kwargs)


class ShiftUsedLog(models.Model):
    production = models.ForeignKey(
        Production,
        related_name="used_logs",
        on_delete=models.CASCADE,
        null=True,
    )
    alloy = models.CharField(max_length=100, null=True, blank=True)
    log_qty = models.FloatField()

    class Meta:
        db_table = "shift_used_log"
