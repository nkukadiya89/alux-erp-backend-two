from django.db import models
from product.models import Alloy, Temper
from settings.models import BaseModule
from production.models import Production
from die.models import Die, DieTool
from shift.models import ShiftSnapshotMixin
from datetime import datetime

class AgeingBatch(ShiftSnapshotMixin, BaseModule):
    STATUS_CHOICES = (
        ("In-Process", "In-Process"),
        ("Completed", "Completed"),
    )
    batch_no = models.CharField(max_length=100, unique=True)
    heat_treatment_no = models.CharField(max_length=100, null=True, blank=True)
    ageing_date = models.DateField(null=True, blank=True)
    furnace_no = models.CharField(max_length=100, null=True, blank=True)
    temperature = models.CharField(max_length=50, null=True, blank=True)
    soaking_time = models.TimeField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    gas_reading_start = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    gas_reading_end = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    cycle_time = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, default="In-Process")

    def save(self, *args, **kwargs):

        if self.start_time and self.end_time:
            start = datetime.combine(datetime.today(), self.start_time)
            end = datetime.combine(datetime.today(), self.end_time)

            diff = end - start
            total_minutes = diff.total_seconds() / 60

            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)

            self.cycle_time = f"{hours}:{minutes:02d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.batch_no

    class Meta:
        db_table = "ageing_batch"
        permissions = [
            ("print_aging_report_pdf_copy", "Can print aging report PDF"),
            ("print_aging_report_excel_copy", "Can print aging report Excel"),
        ]


class AgeingBatchDetail(BaseModule):
    SIDE_CHOICES = [
        ("LHS", "LHS"),
        ("RHS", "RHS"),
    ]

    DEPTH_CHOICES = [("FRONT", "FRONT"), ("MIDDLE", "MIDDLE"), ("BACK", "BACK")]

    POSITION_CHOICES = [("TOP", "TOP"), ("MIDDLE", "MIDDLE"), ("BOTTOM", "BOTTOM")]
    ageing_batch = models.ForeignKey(
        AgeingBatch, on_delete=models.CASCADE, related_name="batch_details"
    )
    production_no = models.ForeignKey(
        Production,
        on_delete=models.CASCADE,
        related_name="ageing_batch_production",
        null=True,
        blank=True,
    )
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, null=True, blank=True)
    depth = models.CharField(
        max_length=10, choices=DEPTH_CHOICES, null=True, blank=True
    )
    position = models.CharField(
        max_length=10, choices=POSITION_CHOICES, null=True, blank=True
    )
    rack_no = models.IntegerField(null=True, blank=True)
    section_no = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="ageing_batch_die",
        null=True,
        blank=True,
    )
    die_no = models.ForeignKey(
        DieTool,
        on_delete=models.CASCADE,
        related_name="ageing_batch_die_tool",
        null=True,
        blank=True,
    )
    cast_no = models.CharField(max_length=100, null=True, blank=True)
    cut_length_mm = models.IntegerField(null=True, blank=True)
    pieces = models.IntegerField(null=True, blank=True)
    weight_per_piece = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    total_weight = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ageing_batch_alloy",
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ageing_batch_temper",
    )
    remark = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.ageing_batch.batch_no} - {self.section_no.die_number if self.section_no else 'No Die'}"


class AgeingTemperatureLog(BaseModule):
    ageing_batch = models.ForeignKey(
        AgeingBatch, on_delete=models.CASCADE, related_name="temperature_logs"
    )
    log_time = models.TimeField(null=True, blank=True)
    zone1_temp = models.DecimalField(
        decimal_places=2, max_digits=6, null=True, blank=True
    )
    zone2_temp = models.DecimalField(
        decimal_places=2, max_digits=6, null=True, blank=True
    )
    zone3_temp = models.DecimalField(
        decimal_places=2, max_digits=6, null=True, blank=True
    )
    zone4_temp = models.DecimalField(
        decimal_places=2, max_digits=6, null=True, blank=True
    )
    deviation = models.BooleanField(default=False)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.ageing_batch.batch_no} - {self.log_time}"
