from django.db import models
from settings.models import BaseModule
from django.conf import settings
from store.models import Store
from customer.models import Customer
from product.models import Item
from purchase_order.models import PurchaseOrder, PurchaseOrderDetail

class GoodsReceiptNote(BaseModule):
    GRN_STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("RECEIVED", "Received"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )
    grn_no = models.CharField(max_length=50, unique=True, db_index=True)
    grn_date = models.DateField(null=True, blank=True)
    invoice_no = models.CharField(max_length=100, null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    challan_no = models.CharField(max_length=100, null=True, blank=True)
    challan_date = models.DateField(null=True, blank=True)
    vendor = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="grn_vendor", null=True, blank=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="grn_po",  null=True, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,null=True, blank=True, related_name="grn_received")
    remarks = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=GRN_STATUS_CHOICES, default="DRAFT")

    def __str__(self):
       return f"{self.grn_no}"

    class Meta:
        permissions = [
            ("download_grn_header_excel_copy", "Can download GRN header Excel"),
            ("download_grn_header_pdf_copy", "Can download GRN header PDF"),
        ]

class GoodsReceiptNoteDetail(BaseModule):
    grn = models.ForeignKey(GoodsReceiptNote, on_delete=models.CASCADE, related_name="grn_details", null=True, blank=True)
    po_detail = models.ForeignKey(PurchaseOrderDetail, on_delete=models.PROTECT, related_name="po_details", null=True, blank=True) 
    excess_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True,blank=True)
    ordered_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    received_qty = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    batch_no = models.CharField(max_length=50, null=True, blank=True)
    heat_no = models.CharField(max_length=50, null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.po_detail.item.item_code} - {self.received_qty}"

    class Meta:
        permissions = [
            ("download_grn_detail_excel_copy", "Can download GRN detail Excel"),
            ("download_grn_detail_pdf_copy", "Can download GRN detail PDF"),
        ]