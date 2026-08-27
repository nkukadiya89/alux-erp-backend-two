from django.db import models
from settings.models import BaseModule
from production.models import Production
from workorder.models import WorkOrder
from customer.models import Customer
from die.models import Die, DieTool
from product.models import Alloy, Temper
from die.models import DiePress
from shift.models import ShiftSnapshotMixin


class DimensionInspection(ShiftSnapshotMixin, BaseModule):
    QUENCHING_TYPE_CHOICES = (
        ("AIR", "AIR"),
        ("WATER_SPRAY", "WATER SPRAY"),
        ("MIST", "MIST"),
        ("WATER_DIP", "WATER_DIP"),
    )
    inspection_date = models.DateField(db_index=True)
    production = models.ForeignKey(
        Production,
        on_delete=models.CASCADE,
        null=True,
        related_name="production_dimension_inspection",
        db_index=True,
    )
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        null=True,
        related_name="workorder_dimension_inspection",
        db_index=True,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        related_name="customer_dimension_inspection",
        db_index=True,
    )
    section = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        null=True,
        related_name="section_dimension_inspection",
        db_index=True,
    )
    cut_length = models.IntegerField(null=True, blank=True)
    container_temp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    die_no = models.ForeignKey(
        DieTool,
        on_delete=models.CASCADE,
        null=True,
        related_name="die_no_dimension_inspection",
        db_index=True,
    )
    wt_mtr = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    front_end_scrap = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    back_end_scrap = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    head_end_scrap = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tail_end_scrap = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    total_scrap = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    quenching_type = models.CharField(
        max_length=100, choices=QUENCHING_TYPE_CHOICES, null=True, blank=True
    )
    butt_end = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    billet_length = models.IntegerField(null=True, blank=True)
    billet_cast_no = models.CharField(max_length=100, null=True, blank=True)
    die_unloading_reason = models.JSONField(blank=True, null=True)
    sample_checked = models.JSONField(blank=True, null=True)
    die_unloading_other = models.CharField(max_length=50, null=True, blank=True)
    die_temp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    extrusion_speed = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    planned_billet = models.IntegerField(null=True, blank=True)
    cooling_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    extruded_billet = models.IntegerField(null=True, blank=True)
    pullar_force_kgs = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    billet_temp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    section_exit_temp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    remarks = models.TextField(null=True, blank=True)

    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        null=True,
        related_name="alloy_dimension_inspection",
        db_index=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        null=True,
        related_name="temper_dimension_inspection",
        db_index=True,
    )
    press = models.ForeignKey(
        DiePress,
        on_delete=models.CASCADE,
        null=True,
        related_name="press_dimension_inspection",
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["inspection_date", "production"]),
            models.Index(fields=["workorder", "customer"]),
            models.Index(fields=["section", "alloy", "temper"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["deleted", "inspection_date"]),
        ]

        permissions = [
            (
                "download_dimension_inspection_excel_copy",
                "Can download dimension inspection Excel",
            ),
            (
                "download_dimension_inspection_pdf_copy",
                "Can download dimension inspection PDF",
            ),
        ]

    def __str__(self):
        return f"Inspection {self.id} - {self.inspection_date}"


class DimensionInspectionDetail(BaseModule):
    dimension_inspection = models.ForeignKey(
        DimensionInspection,
        on_delete=models.CASCADE,
        related_name="dimension_inspection_details",
        db_index=True,
    )
    nominal = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tolerance = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    before_cav_1 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_2 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_3 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_4 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_5 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_6 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_7 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_8 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_9 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    before_cav_10 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    after_cav_1 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_2 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_3 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_4 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_5 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_6 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_7 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_8 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_9 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    after_cav_10 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["dimension_inspection", "created_at"]),
        ]

    def __str__(self):
        return f"Inspection Detail {self.nominal}"
