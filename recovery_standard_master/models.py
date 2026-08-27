from django.db import models
from settings.models import BaseModule
from furnace_master.models import FurnaceMaster
from material.models import Material

class RecoveryStandardMaster(BaseModule):
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
      )
    

    furnace_type = models.ForeignKey(FurnaceMaster, on_delete=models.PROTECT, null=True, blank=True)
    material_type = models.ForeignKey( Material,on_delete=models.PROTECT, null=True, blank=True)
    min_recovery_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    max_recovery_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    standard_loss_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    

    def __str__(self):
        return f"{self.furnace_type} - {self.material_type}"

    class Meta:
        permissions = [
            ("download_recovery_standard_excel", "Can download Recovery Standard Excel"),
            ("download_recovery_standard_pdf", "Can download Recovery Standard PDF"),
        ]