from django.db import models
from customer.models import Customer
from product.models import Item
from settings.models import BaseModule
from store.models import Store

class PurchaseOrder(BaseModule):
    PO_STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("PARTIALLY_RECEIVED", "Partially Received"),
        ("FULLY_RECEIVED", "Fully Received"),
        ("CANCELLED", "Cancelled"),
        ("CLOSED", "Closed"),
    )
    po_no = models.CharField(max_length=100, unique=True, editable=False)
    payment_terms = models.TextField(max_length=100, null=True,blank=True)
    material_indent = models.ForeignKey('material_indent.MaterialIndent', on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="po_vendor")
    po_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    request_no = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=30, choices=PO_STATUS_CHOICES, default="DRAFT")
      

    def __str__(self):
        return f"{self.po_no} - {self.po_date}"
    
    class Meta:
        permissions = [
            ("download_purchase_order_excel_copy", "Can download purchase order Excel"),
            ("download_purchase_order_pdf_copy", "Can download purchase order PDF"),
        ]
 
 
class PurchaseOrderDetail(BaseModule):
    GST_TYPE_CHOICES = (("IGST", "IGST"), ("SGST_CGST", "SGST_CGST"))
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="po_details", null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True, related_name="po_item")
    ordered_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    received_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)   
    basic_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    store = models.ForeignKey(Store,on_delete=models.CASCADE, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True,blank=True)
    gst_type = models.CharField(max_length=15, choices=GST_TYPE_CHOICES, null=True, blank=True)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    transport_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    forwarding_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hsn_code = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f"{self.item.item_name} - {self.rate}"
    
    class Meta:
        permissions = [
            ("download_purchase_order_detail_excel_copy", "Can download purchase order detail Excel"),
            ("download_purchase_order_detail_pdf_copy", "Can download purchase order detail PDF"),
        ]