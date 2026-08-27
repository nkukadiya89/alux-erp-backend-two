from django.db import models
from settings.models import BaseModule


class VehicleType(BaseModule):
    vehicle_type = models.CharField(
        max_length=200, null=False, blank=False, unique=True
    )

    def __str__(self):
        return f"{self.vehicle_type}"

    class Meta:
        db_table = "vehicle_type"

        permissions = [
            ("download_vehicle_type_excel_copy", "Can download vehicle type Excel"),
            ("download_vehicle_type_pdf_copy", "Can download vehicle type PDF"),
        ]
