from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from settings.models import BaseModule
from shift.models import ShiftSnapshotMixin
from die.models import DiePress, Die
from production.models import Production
from product.models import Alloy, Temper


class OnlineInspection(ShiftSnapshotMixin, BaseModule):
    inspection_date = models.DateField()
    press = models.ForeignKey(
        DiePress, on_delete=models.CASCADE, related_name="online_inspections"
    )

    def __str__(self):
        return f"Inspection {self.id} - {self.inspection_date}"

    class Meta:
        db_table = "online_inspection"
        indexes = [
            models.Index(fields=["-inspection_date", "deleted"]),
            models.Index(fields=["press", "deleted"]),
        ]

        permissions = [
            ("print_online_inspection_pdf_copy", "Can print online inspection PDF"),
            (
                "print_online_inspection_report_excel_copy",
                "Can print online inspection Excel",
            ),
            (
                "print_online_inspection_report_pdf_copy",
                "Can print online inspection report PDF",
            ),
        ]


class OnlineInspectionDetail(BaseModule):
    online_inspection = models.ForeignKey(
        OnlineInspection, on_delete=models.CASCADE, related_name="qc_rack_details"
    )
    production = models.ForeignKey(
        Production,
        on_delete=models.CASCADE,
        related_name="inspection_details",
        null=True,
        blank=True,
    )
    section = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="inspection_details",
        null=True,
        blank=True,
    )
    cut_length_mm = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        related_name="online_inspection_details",
        null=True,
        blank=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="online_inspection_details",
        null=True,
        blank=True,
    )
    planned_pieces = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    act_inspected_pieces = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    bend_twist = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    blister = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    scoring = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    scratch = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    damage = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    joint = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    dimension = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    concave = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    hardness = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    line = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    section_cut = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    core_defect = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    chattering = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    roughness_pickup = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    rack_no = models.CharField(max_length=100, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Detail {self.id} - Inspection {self.online_inspection_id}"

    class Meta:
        db_table = "online_inspection_detail"
        indexes = [
            models.Index(fields=["online_inspection", "deleted"]),
            models.Index(fields=["production", "deleted"]),
            models.Index(fields=["section", "deleted"]),
        ]
