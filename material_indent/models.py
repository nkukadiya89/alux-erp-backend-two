from django.db import models
from settings.models import BaseModule
from common.models import Department
from product.models import Item, UOM
from store.models import Store
from utils.generate_number import generate_material_indent_no

class MaterialIndent(BaseModule):
    PRIORITY_CHOICES = (
        ("Normal", "Normal"),
        ("Low", "Low"),
        ("High", "High"),   
        
    )
    indent_no = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    required_date = models.DateField(null=True, blank=True)
    priority = models.CharField(choices=PRIORITY_CHOICES, default="Normal", max_length=10, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.indent_no:
            self.indent_no = generate_material_indent_no()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.priority}"
    
    class Meta:
        permissions = [
            ("download_material_indent_excel_copy", "Can download material indent Excel"),
            ("download_material_indent_pdf_copy", "Can download material indent PDF"),
        ]

    
class MaterialIndentDetail(BaseModule):
    material_indent = models.ForeignKey(MaterialIndent, on_delete=models.SET_NULL, null=True, blank=True, related_name="material_indent")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True)
    available_qty = models.DecimalField(max_length=10, decimal_places=3, max_digits=10, default=0.00, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    requested_qty = models.DecimalField(max_length=10, decimal_places=2, max_digits=10, default=0.00, blank=True, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True)
    uom = models.ForeignKey(UOM, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.item} - {self.requested_qty}"

    
    class Meta:
        permissions = [
            ("download_material_indent_detail_excel_copy", "Can download material indent detail Excel"),
            ("download_material_indent_detail_pdf_copy", "Can download material indent detail PDF"),
        ]