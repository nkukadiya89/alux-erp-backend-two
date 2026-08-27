from django.db import models
from settings.models import BaseModule
from aging.models import AgeingBatch
from production.models import Production
from die.models import Die, DieTool
from product.models import Alloy, Temper
from shift.models import ShiftSnapshotMixin


class MechanicalTest(ShiftSnapshotMixin, BaseModule):
    SOURCE_TYPE_CHOICES = (("PRODUCTION", "PRODUCTION"), ("AGEING", "AGEING"))
    qc_date = models.DateField(auto_now_add=True)
    source_type = models.CharField(
        max_length=20, choices=SOURCE_TYPE_CHOICES, null=True, blank=True
    )
    ageing_batch_no = models.ForeignKey(
        AgeingBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mechanical_test_ageing",
    )
    heat_treatment_no = models.CharField(max_length=100, null=True, blank=True)
    furnace_no = models.CharField(max_length=100, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return self.source_type

    class Meta:
        permissions = [
            ("print_mechanical_test_excel_copy", "Can print mechanical test Excel"),
            ("print_mechanical_test_pdf_copy", "Can print mechanical test PDF"),
        ]


class MechanicalTestDetail(BaseModule):
    mechanical_test = models.ForeignKey(
        MechanicalTest, on_delete=models.CASCADE, related_name="test_details"
    )
    production_no = models.ForeignKey(
        Production,
        on_delete=models.CASCADE,
        null=True,
        related_name="mechanical_test_detail_production_no",
    )
    rack_no = models.IntegerField(null=True, blank=True)
    section_no = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        null=True,
        related_name="mechanical_test_detail_section_no",
    )
    die_no = models.ForeignKey(
        DieTool,
        on_delete=models.CASCADE,
        null=True,
        related_name="mechanical_test_detail_die_no",
    )
    cast_no = models.CharField(max_length=100, null=True, blank=True)
    cut_length_mm = models.IntegerField(null=True, blank=True)
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        null=True,
        related_name="mechanical_test_detail_alloy",
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        null=True,
        related_name="mechanical_test_detail_temper",
    )
    pieces = models.IntegerField(null=True, blank=True)
    total_weight = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    hardness_bhn = models.IntegerField(null=True, blank=True)
    conductivity_iacs = models.IntegerField(null=True, blank=True)
    qc_result = models.CharField(max_length=20, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.mechanical_test.furnace_no
