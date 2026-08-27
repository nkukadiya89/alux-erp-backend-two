from django.db import models
from product.models import Item
from settings.models import BaseModule
from common.models import Department, UOM
from utils.generate_number import generate_material_request_no


class MaterialRequest(BaseModule):
    request_no = models.CharField(max_length=100, unique=True, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.request_no:
            self.request_no = generate_material_request_no()
            
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.request_no}"
    
    class Meta:
        permissions = [
            ("download_material_request_excel_copy", "Can download material request Excel"),
            ("download_material_request_pdf_copy", "Can download material request PDF"),
        ]

class MaterialRequestDetail(BaseModule):
    material_request = models.ForeignKey(MaterialRequest, on_delete=models.CASCADE, related_name="material_request_detail", null=True,  blank=True)
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True,blank=True)
    description = models.TextField(null=True, blank=True)
    unit = models.ForeignKey(UOM, on_delete=models.SET_NULL, null=True, blank=True)
    required_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    available_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    issue_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarks = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.required_qty} - {self.available_qty}"
    
    
    class Meta:
        permissions = [
            ("download_material_request_detail_excel_copy", "Can download Material request detail Excel"),
            ("download_material_request_detail_pdf_copy", "Can download Material request detail PDF"),
        ]
