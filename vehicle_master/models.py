from django.db import models
from settings.models import BaseModule
from transporter.models import Transporter
from vehicle_type.models import VehicleType
from simple_history.models import HistoricalRecords

class VehicleMaster(BaseModule):
    history = HistoricalRecords()
    party_name = models.ForeignKey(
        Transporter,
        null=True,
        on_delete=models.CASCADE,
        related_name="vehicle_master_party_name",
        db_index=True,
    )
    vehicle_no = models.CharField(max_length=30, unique=True, null=True, blank=True, db_index=True)
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_master_vehicle_type",
        db_index=True,
    )
    tare_wt = models.DecimalField(
        max_digits=30, decimal_places=3, null=True, blank=True
    )

    def __str__(self):
        return f"{self.vehicle_no}"

    class Meta:
        db_table = "vehicle_master"
        indexes = [
            models.Index(fields=["deleted", "-id"]),
            models.Index(fields=["deleted", "party_name"]),
            models.Index(fields=["deleted", "vehicle_type"]),
            models.Index(fields=["vehicle_no"]),
        ]
        permissions = [
            ("download_vehicle_master_excel_copy", "Can download vehicle master Excel"),
            ("download_vehicle_master_pdf_copy", "Can download vehicle master PDF"),
        ]
