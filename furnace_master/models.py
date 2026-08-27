from django.db import models
from settings.models import BaseModule  

class FurnaceMaster(BaseModule):
    FURNACE_TYPE_CHOICES = (
        ("CRUCIBLE", "Crucible"),
        ("CRUCIBLE_FURNACE", "Crucible Furnace"),
        ("ELECTRIC", "Electric"),
        ("ELECTRIC_ARC_FURNACE", "Electric Arc Furnace"),
        ("GAS", "Gas"),
        ("GAS_FURNACE", "Gas Furnace"),
        ("HOLDING", "Holding"),
        ("INDUCTION", "Induction"),
        ("INDUCTION_FURNACE", "Induction Furnace"),
        ("OIL_FURNACE", "Oil Furnace"),
        ("REVERBERATORY", "Reverberatory"),
        ("REVERBERATORY_FURNACE", "Reverberatory Furnace"),
        ("ROTARY", "Rotary"),
        ("TILTING", "Tilting"),
    )

    FUEL_TYPE_CHOICES = (
        ("COAL", "Coal"),
        ("DIESEL", "Diesel"),
        ("ELECTRICITY", "Electricity"),
        ("HEAVY_FUEL_OIL", "Heavy Fuel Oil"),
        ("LPG", "LPG"),
        ("NATURAL_GAS", "Natural Gas"),
        ("PROPANE", "Propane"),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    type = models.CharField(max_length=50, choices=FURNACE_TYPE_CHOICES)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Capacity (KG)", null=True, blank=True)
    min_temp_celsius = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Min Temp (°C)", blank=True, null=True)
    max_temp_celsius = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Max Temp (°C)", blank=True, null=True)
    fuel_type = models.CharField(max_length=50, choices=FUEL_TYPE_CHOICES)
    remarks = models.TextField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
   
    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        permissions = [
            ("download_furnace_Master_excel_copy", "Can download furnace master Excel"),
            ("download_furnace_Master_pdf_copy", "Can download furnace master PDF"),
        ]


