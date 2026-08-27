from django.conf import settings
from django.db import models

from die.models import Die
from die_requisition.models import DieRequisition, DieRequisitionDetail
from settings.models import BaseModule
from workorder.models import WorkOrder, WorkOrderDetail
from ageing_cycle.models import AgingCycle

class Planning(BaseModule):
    QUENCHING_TYPE_CHOICES = (
        ("AIR", "AIR"),
        ("WATER_SPRAY", "WATER SPRAY"),
        ("MIST", "MIST"),
        ("WATER_DIP", "WATER_DIP"),
    )
    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Submitted", "Submitted"),
        ("Approved", "Approved"),
        ("Scheduled", "Scheduled"),
        ("In-Progress", "In-Progress"),
        ("Partially-Closed", "Partially-Closed"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("On-Hold", "On-Hold"),
    )
    profile_no = models.ForeignKey(
        Die, on_delete=models.CASCADE, related_name="planning_profile_no"
    )
    die_requisition = models.ForeignKey(
        DieRequisition,
        on_delete=models.CASCADE,
        related_name="planning_die_requisition",
        null=True,
        blank=True,
    )
    die_requisition_detail = models.ForeignKey(
        DieRequisitionDetail,
        on_delete=models.CASCADE,
        related_name="planning_die_requisition_detail",
        null=True,
        blank=True,
    )
    workorder = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="planning_workorder"
    )
    workorder_detail = models.ForeignKey(
        WorkOrderDetail,
        on_delete=models.CASCADE,
        related_name="planning_workorder_detail",
        null=True,
    )
    ageing = models.ForeignKey(
        AgingCycle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planning_ageing_cycle",
    )
    quenching_type = models.CharField(
        max_length=100, choices=QUENCHING_TYPE_CHOICES, null=True, blank=True
    )
    water_pressure = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    flow_rate = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    planning_no = models.CharField(max_length=100, null=True)
    planning_date = models.DateField(auto_now=True)
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="planning_scheduled_by",
        null=True,
        blank=True,
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    scheduling_remarks = models.TextField(null=True, blank=True)

    plan_pcs = models.IntegerField(default=0, null=True)
    plan_qty = models.FloatField(default=0.0, null=True)
    butt_weight_kg = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    process_loss_mt = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    remarks = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Draft")
    cancel_status = models.TextField(null=True, blank=True)
    hold_status = models.TextField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="planning_submitted_by",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="planning_approved_by",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_remarks = models.TextField(null=True, blank=True)

    blt_size_mm = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    blt_size_inch = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    bltWt = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    butt_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    actbltWt = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    weight_per_piece = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    total_order_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    ext_len_mm = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    process_loss = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    act_ext_len = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    no_of_pieces = models.IntegerField(default=0, null=True, blank=True)
    pieces_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    process_recovery = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    totalWastage = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    totalBillets = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    totalKgs = models.DecimalField(decimal_places=3, max_digits=10, null=True, blank=True)
    billet_remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.planning_no} - {self.profile_no}"

    class Meta:
        db_table = "planning"

        indexes = [
            models.Index(fields=["planning_no"], name="idx_planning_no"),
            models.Index(fields=["status"], name="idx_planning_status"),
            models.Index(fields=["planning_date"], name="idx_planning_date"),
            models.Index(fields=["scheduled_date"], name="idx_planning_scheduled_date"),
            models.Index(fields=["workorder", "status"], name="idx_workorder_status"),
            models.Index(fields=["profile_no", "status"], name="idx_profile_status"),
            models.Index(
                fields=["die_requisition", "status"], name="idx_die_req_status"
            ),
        ]

        permissions = [
            ("download_planning_pdf_copy", "Can download planning PDF"),
            ("download_planning_excel_copy", "Can download planning Excel"),
            (
                "download_planning_priority_pdf_copy",
                "Can download planning priority PDF",
            ),
            (
                "download_planning_priority_excel_copy",
                "Can download planning priority Excel",
            ),
        ]
