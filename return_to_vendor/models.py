from django.db import models
from settings.models import BaseModule
from customer.models import Customer

class ReturnToVendor(BaseModule):

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("REPLACED", "Replaced"),
        ("CLOSED", "Closed"),
        ("PENDING", "Pending"),
    )


    grn = models.ForeignKey("receipt_notes.GoodsReceiptNote", on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    item = models.ForeignKey("material.Material", on_delete=models.CASCADE, null=True, blank=True)
    rejected_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    reason_for_return = models.TextField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="REPLACED", null=True, blank=True)

    def __str__(self):
        return str(self.grn)

    class Meta:
        permissions = [
            ("download_rtv_excel_copy", "Can download RTV Excel"),
            ("download_rtv_pdf_copy", "Can download RTV PDF"),
        ]