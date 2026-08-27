from django.db import models
from settings.models import BaseModule
from furnace_master.models import FurnaceMaster
from store.models import Store
from shift.models import ShiftSnapshotMixin


class DrossEntry(BaseModule, ShiftSnapshotMixin):
    dross_entry_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    heat_no = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    furnace = models.ForeignKey(FurnaceMaster, on_delete=models.PROTECT, null=True, blank=True)

    
    def __str__(self):
        return f"{self.dross_entry_no} - {self.furnace}"
    
    class Meta:
        permissions = [
            ("download_dross_entry_excel_copy", "Can download dross entry Excel"),
            ("download_dross_entry_pdf_copy", "Can download dross entry PDF"),
        ]
    
    
class DrossDetail(BaseModule):
    dross_entry = models.ForeignKey(DrossEntry, on_delete=models.CASCADE, related_name="dross_details", null=True, blank=True)
    DROSS_TYPE_CHOICES = (
        ("WHITE_DROSS", "White Dross"),
        ("BLACK_DROSS", "Black Dross"),
        ("SKIMMING_DROSS", "Skimming Dross"),
        ("FURNACE_DROSS", "Furnace Dross"),
    )

    dross_type = models.CharField(max_length=50, choices=DROSS_TYPE_CHOICES, null=True, blank=True)
    dross_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.PROTECT, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    
    
    def __str__(self):
     return f"{self.dross_type} - {self.store}" if self.store else f"{self.dross_type}"
    
    
    class Meta:
        permissions= [
            ("download_dross_detail_excel_copy", "Can download dross detail Excel"),
            ("download_dross_detail_pdf_copy", "Can download dross detail PDF"),
        ]