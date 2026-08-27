from django.db import models

from common.models import JobWorkType, Plant
from customer.models import Customer
from die.models import Die, DieTool
from jobwork_invoice.models import JobworkInvoice
from product.models import Alloy, Temper
from production.models import Production
from settings.models import BaseModule
from shift.models import ShiftSnapshotMixin
from workorder.models import WorkOrder, WorkOrderDetail


class ReturnQC(ShiftSnapshotMixin, BaseModule):
    """
    Return QC Inspection after material returns from third-party jobwork vendor.
    Creating a record advances Process Tracking to JW_RETURN_QC.
    """

    QC_RESULT_CHOICES = (
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
        ("REWORK", "Rework"),
        ("PARTIAL", "Partial Pass"),
    )

    inspection_no = models.CharField(max_length=50, unique=True, db_index=True)
    inspection_date = models.DateField(db_index=True)
    vendor = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="return_qc_inspections",
        limit_choices_to={"company_type__in": ["vendor", "customer_vendor"]},
    )
    jobwork_invoice = models.ForeignKey(
        JobworkInvoice,
        on_delete=models.SET_NULL,
        related_name="return_qc_inspections",
        null=True,
        blank=True,
    )
    jobwork_type = models.ForeignKey(
        JobWorkType,
        on_delete=models.PROTECT,
        related_name="return_qc_inspections",
        null=True,
        blank=True,
    )
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        related_name="return_qc_inspections",
        null=True,
        blank=True,
    )
    vehicle_no = models.CharField(max_length=50, blank=True, null=True)
    gate_entry_ref = models.CharField(max_length=100, blank=True, null=True)
    overall_result = models.CharField(
        max_length=20, choices=QC_RESULT_CHOICES, default="PASS"
    )
    remarks = models.TextField(blank=True, null=True)
    attachment = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "return_qc"
        ordering = ["-inspection_date", "-id"]
        permissions = [
            ("print_return_qc_pdf_copy", "Can print return QC PDF"),
            ("print_return_qc_excel_copy", "Can print return QC Excel"),
        ]

    def __str__(self):
        return self.inspection_no


class ReturnQCLine(BaseModule):
    return_qc = models.ForeignKey(
        ReturnQC, on_delete=models.CASCADE, related_name="qc_lines"
    )
    production = models.ForeignKey(
        Production,
        on_delete=models.PROTECT,
        related_name="return_qc_lines",
    )
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.SET_NULL,
        related_name="return_qc_lines",
        null=True,
        blank=True,
    )
    workorder_detail = models.ForeignKey(
        WorkOrderDetail,
        on_delete=models.SET_NULL,
        related_name="return_qc_lines",
        null=True,
        blank=True,
    )
    section_no = models.ForeignKey(
        Die,
        on_delete=models.SET_NULL,
        related_name="return_qc_lines_section",
        null=True,
        blank=True,
    )
    die_no = models.ForeignKey(
        DieTool,
        on_delete=models.SET_NULL,
        related_name="return_qc_lines_die",
        null=True,
        blank=True,
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.SET_NULL,
        related_name="return_qc_lines_alloy",
        null=True,
        blank=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.SET_NULL,
        related_name="return_qc_lines_temper",
        null=True,
        blank=True,
    )
    pieces_sent = models.IntegerField(null=True, blank=True)
    pieces_received = models.IntegerField(null=True, blank=True)
    pieces_accepted = models.IntegerField(null=True, blank=True)
    pieces_rejected = models.IntegerField(null=True, blank=True)
    cut_length_mm = models.IntegerField(null=True, blank=True)
    weight_received = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    qc_result = models.CharField(
        max_length=20,
        choices=ReturnQC.QC_RESULT_CHOICES,
        default="PASS",
        blank=True,
        null=True,
    )
    defect_type = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "return_qc_line"
        ordering = ["id"]

    def __str__(self):
        return f"{self.return_qc_id} - {self.production_id}"
