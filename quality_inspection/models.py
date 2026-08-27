from django.db import models
from settings.models import BaseModule
from django.conf import settings
from receipt_notes.models import GoodsReceiptNote, GoodsReceiptNoteDetail
from purchase_order.models import PurchaseOrder
from customer.models import Customer

class QualityInspection(BaseModule):
    INSPECTION_TYPE_CHOICES = (
        ("VISUAL", "Visual Inspection"),
        ("DIMENSIONAL", "Dimensional Inspection"),
        ("CHEMICAL", "Chemical Testing"),
    )   
    
    INSPECTION_STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("PASSED", "Passed"),
        ("FAILED", "Failed"),
        ("PARTIAL", "Partially Accepted"),
    )
    inspection_no = models.CharField(max_length=100, null=True, blank=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="quality_inspection_purchase_order",
        null=True,
    )
    grn = models.ForeignKey(
        GoodsReceiptNote,
        on_delete=models.PROTECT,
        related_name="quality_inspection_grn",
        null=True,
    )
    vendor = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="quality_inspection_vendor",
        null=True,
    )
    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    inspection_type = models.CharField(max_length=50, choices=INSPECTION_TYPE_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=30, choices=INSPECTION_STATUS_CHOICES, default="PENDING")
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Inspection on {self.inspection_date} - Status: {self.status}"
    
    class Meta:
        permissions = [
            ("download_quality_inspection_excel_copy", "Can download quality inspection Excel"),
            ("download_quality_inspection_pdf_copy", "Can download quality inspection PDF"),
        ]

class QualityInspectionDetail(BaseModule):
    QC_DETAIL_STATUS_CHOICES = (
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
        ("PARTIAL", "Partial"),
    )
    quality_inspection = models.ForeignKey(
        QualityInspection,
        on_delete=models.PROTECT,
        related_name="inspection_details"
    )
    grn_detail = models.ForeignKey(
        GoodsReceiptNoteDetail,
        on_delete=models.PROTECT,
        related_name="quality_inspection_details"
    )
    received_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    sample_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    accepted_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    rejected_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    result = models.CharField(max_length=30, choices=QC_DETAIL_STATUS_CHOICES, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Detail for {self.quality_inspection.inspection_no}"
