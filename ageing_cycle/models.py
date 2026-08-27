from django.db import models
from settings.models import BaseModule
from product.models import Alloy, Temper

class AgingCycle(BaseModule):
    COOLING_TYPE_CHOICES = [
        ("Air_Cooling", "Air_Cooling"),
        ("Fan_Cooling", "Fan_Cooling"),
        ("Natural_Cooling", "Natural_Cooling"),
        ("Water_Quench", "Water_Quench"),
        ("Water_Spray_Cooling", "Water_Spray_Cooling"),
        ("Forced_Air_Cooling", "Forced_Air_Cooling"),
    ]
    cycle_code = models.CharField(max_length=100, null=True, blank=True)
    cycle_name = models.CharField(max_length=255, null=True, blank=True)
    alloy = models.ForeignKey(Alloy, on_delete=models.SET_NULL, null=True, blank=True)
    temper = models.ForeignKey(Temper, on_delete=models.SET_NULL, null=True, blank=True)
    zone1_temp = models.CharField(max_length=100, null=True, blank=True)
    zone2_temp = models.CharField(max_length=100, null=True, blank=True)
    zone3_temp =models.CharField(max_length=100, null=True, blank=True)
    zone4_temp = models.CharField(max_length=100, null=True, blank=True)
    soaking_time = models.CharField(max_length=50, null=True, blank=True)
    cooling_type = models.CharField(max_length=50, null=True, blank=True, choices=COOLING_TYPE_CHOICES)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "aging_cycle"

    def __str__(self):
        return self.cycle_name