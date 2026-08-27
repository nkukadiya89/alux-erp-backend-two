from django.db import models
from django.conf import settings
from settings.models import BaseModule
from furnace_master.models import FurnaceMaster
from product.models import Alloy
from material.models import Material
from store. models import Store



SHIFT_CHOICES = (
    ("A", "Shift A"),
    ("B", "Shift B"),
    ("C", "Shift C"),
    ("GENERAL", "General"),
)

STATUS_CHOICES = (
    ("DRAFT", "Draft"),
    ("APPROVED", "Approved"),
    ("USED IN HEAT", "Used in heat"),
    ("ARCHIVED", "Archived"),
)


class FurnaceChargePlan(BaseModule):
    plan_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    furnace = models.ForeignKey(FurnaceMaster, on_delete=models.PROTECT, null=True, blank=True)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, null=True, blank=True)
    alloy_type = models.ForeignKey(Alloy, on_delete=models.PROTECT, null=True, blank=True)
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    target_heat_weight = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField( max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    
    def __str__(self):
        return str(self.plan_no)

    class Meta:
        permissions = [
            (
            "download_furnace_charge_plan_excel","Can download Furnace Charge Plan Excel"),
            ("download_furnace_charge_plan_pdf", "Can download Furnace Charge Plan PDF"),
        ]


class FurnaceChargePlanDetail(BaseModule):
    furnace_charge_plan = models.ForeignKey(FurnaceChargePlan,on_delete=models.CASCADE, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.PROTECT, null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.PROTECT, null=True, blank=True)
    available_stock = models.DecimalField(max_digits=12, decimal_places=2,null=True, blank=True)
    planned_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    uom = models.CharField(max_length=20, null=True, blank=True)
    remarks = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.furnace_charge_plan.plan_no} - {self.material}"
    
    
    class Meta:
        permissions = [
            (
            "download_furnace_charge_plan_detail_excel","Can download Furnace Charge Plan Detail Excel"),
            ("download_furnace_charge_plan_detail_pdf", "Can download Furnace Charge Plan Detail PDF"),
        ]