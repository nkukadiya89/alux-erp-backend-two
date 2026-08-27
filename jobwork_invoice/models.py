from django.db import models

from common.models import JobWorkType, Plant
from customer.models import Customer
from die.models import Die, DieTool
from product.models import Alloy, Temper
from production.models import Production
from settings.models import BaseModule
from shift.models import ShiftSnapshotMixin
from workorder.models import WorkOrder, WorkOrderDetail


class JobworkInvoice(ShiftSnapshotMixin, BaseModule):
    """
    Aluminum extrusion Jobwork Challan / Invoice.
    Links third-party vendor jobwork to production lines and advances
    Process Tracking through jobwork stages up to JW_INVOICE_LINKED.

    Vendor is Customer master with company_type vendor / customer_vendor
    (same source as Die Tool / Gate Entry).
    """

    challan_no = models.CharField(max_length=50, unique=True, db_index=True)
    challan_date = models.DateField(db_index=True)
    vendor = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="jobwork_invoices",
        limit_choices_to={"company_type__in": ["vendor", "customer_vendor"]},
    )
    jobwork_type = models.ForeignKey(
        JobWorkType,
        on_delete=models.PROTECT,
        related_name="jobwork_invoices",
        null=True,
        blank=True,
    )
    vendor_invoice_no = models.CharField(max_length=100, blank=True, null=True)
    vendor_invoice_date = models.DateField(blank=True, null=True)
    vehicle_no = models.CharField(max_length=50, blank=True, null=True)
    gate_pass_ref = models.CharField(max_length=100, blank=True, null=True)
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoices",
        null=True,
        blank=True,
    )
    taxable_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, default=0
    )
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, default=0
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, default=0
    )
    remarks = models.TextField(blank=True, null=True)
    attachment = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "jobwork_invoice"
        ordering = ["-challan_date", "-id"]
        permissions = [
            ("print_jobwork_invoice_pdf_copy", "Can print jobwork invoice PDF"),
            ("print_jobwork_invoice_excel_copy", "Can print jobwork invoice Excel"),
        ]

    def __str__(self):
        return self.challan_no


class JobworkInvoiceLine(BaseModule):
    jobwork_invoice = models.ForeignKey(
        JobworkInvoice,
        on_delete=models.CASCADE,
        related_name="invoice_lines",
    )
    production = models.ForeignKey(
        Production,
        on_delete=models.PROTECT,
        related_name="jobwork_invoice_lines",
    )
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoice_lines",
        null=True,
        blank=True,
    )
    workorder_detail = models.ForeignKey(
        WorkOrderDetail,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoice_lines",
        null=True,
        blank=True,
    )
    section_no = models.ForeignKey(
        Die,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoice_lines_section",
        null=True,
        blank=True,
    )
    die_no = models.ForeignKey(
        DieTool,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoice_lines_die",
        null=True,
        blank=True,
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoice_lines_alloy",
        null=True,
        blank=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.SET_NULL,
        related_name="jobwork_invoice_lines_temper",
        null=True,
        blank=True,
    )
    pieces = models.IntegerField(null=True, blank=True)
    cut_length_mm = models.IntegerField(null=True, blank=True)
    total_weight = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    jobwork_description = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "jobwork_invoice_line"
        ordering = ["id"]

    def __str__(self):
        return f"{self.jobwork_invoice_id} - {self.production_id}"
