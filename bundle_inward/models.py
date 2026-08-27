from django.conf import settings
from django.db import models
from django.utils import timezone

from die.models import Die
from product.models import Alloy, Temper
from settings.models import BaseModule
from workorder.models import WorkOrder, WorkOrderDetail
from shift.models import ShiftSnapshotMixin

class BundleInward(BaseModule, ShiftSnapshotMixin):
    STATUS_CHOICES = (
        ("Dispatched", "Dispatched"),
        ("Packed", "Packed"),
        ("Warehouse", "Warehouse"),
        ("Excess-Stock", "Excess-Stock"),
    )
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="bundle_inward_workorder",
        null=True,
        db_index=True,
    )
    workorder_detail = models.ForeignKey(
        WorkOrderDetail,
        on_delete=models.CASCADE,
        related_name="bundle_inward_workorder_detail",
        null=True,
        db_index=True,
    )
    bundle_no = models.CharField(max_length=100, null=True, db_index=True, unique=True)
    pieces = models.IntegerField(default=0)
    weight = models.DecimalField(decimal_places=3, max_digits=10)
    gross_weight = models.DecimalField(decimal_places=3, max_digits=10)
    packing_date = models.DateTimeField(null=True, default=timezone.now, db_index=True)
    dispatch_date = models.DateTimeField(null=True, blank=True, db_index=True)
    hardness = models.CharField(max_length=100, db_index=True)
    remarks = models.TextField(null=True, blank=True)
    status = models.CharField(
        choices=STATUS_CHOICES, default="Packed", max_length=100, db_index=True
    )
    verified = models.BooleanField(default=False, db_index=True)
    verify_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="bundle_verify_by",
        db_index=True,
    )
    verified_date = models.DateTimeField(auto_now=True, null=True)

    added_for_outword = models.BooleanField(default=False, db_index=True)
    added_for_warehouse = models.BooleanField(default=False, db_index=True)

    is_excess_stock = models.BooleanField(default=False, db_index=True)
    is_warehouse = models.BooleanField(default=False, db_index=True)

    @property
    def is_in_warehouse(self):
        """Check if this bundle is in any warehouse (finalized)"""
        return self.warehouse_bundle_inwards.exists()

    @property
    def is_dispatched_from_warehouse(self):
        """Check if this bundle has been dispatched from warehouse"""
        return self.warehouse_bundle_outwards.exists()

    @property
    def is_in_bundle_outward(self):
        """Check if this bundle is in any bundle outward (finalized)"""
        return self.bundle_outward_inwards.exists()

    @property
    def is_dispatched_via_bundle_outward(self):
        """Check if this bundle has been dispatched via bundle outward"""
        return self.bundle_outward_outwards.exists()

    def __str__(self):
        return f"{self.workorder} - {self.bundle_no}"

    class Meta:
        db_table = "bundle_inward"
        indexes = [
            models.Index(fields=["dispatch_date"], name="dispatch_date_idx"),
            models.Index(
                fields=["added_for_warehouse"], name="added_for_warehouse_idx"
            ),
            models.Index(fields=["workorder", "status"], name="workorder_status_idx"),
            models.Index(
                fields=["is_warehouse", "is_excess_stock"], name="warehouse_excess_idx"
            ),
        ]
        permissions = [
            ("print_bundle_inward_copy", "Can print bundle inward"),
            ("download_bundle_inward_excel_copy", "Can download bundle inward Excel"),
            ("print_current_stock_copy", "Can print current stock"),
            ("download_current_stock_excel_copy", "Can download current stock Excel"),
            ("print_packing_report_copy", "Can print packing report"),
            ("download_packing_report_excel_copy", "Can download packing report Excel"),
            ("print_packing_datewise_report_copy", "Can print packing datewise report"),
            (
                "download_packing_datewise_report_excel_copy",
                "Can download packing datewise report Excel",
            ),
        ]


class ExcessStock(BaseModule):

    SHIFT_CHOICES = (
        ("A", "A"),
        ("B", "B"),
    )

    die_profile = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="excess_stock_die",
        null=True,
        db_index=True,
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        related_name="excess_stock_alloy",
        null=True,
        db_index=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="excess_stock_temper",
        null=True,
        db_index=True,
    )
    bundle_inward = models.ForeignKey(
        BundleInward,
        on_delete=models.CASCADE,
        related_name="excess_stock_bundle_inward",
        null=True,
        db_index=True,
    )

    length = models.IntegerField(default=0, null=True, blank=True, db_index=True)
    weight = models.DecimalField(decimal_places=3, max_digits=10)
    gross_weight = models.DecimalField(decimal_places=3, max_digits=10)
    pieces = models.IntegerField(default=0)
    shift = models.CharField(
        choices=SHIFT_CHOICES, default="A", max_length=10, db_index=True
    )
    hardness_value = models.CharField(max_length=100, db_index=True)
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.die_profile} - {self.alloy}"

    class Meta:
        db_table = "excess_stock"
        indexes = [
            models.Index(fields=["bundle_inward"], name="bundle_inward_excess_idx"),
            models.Index(fields=["die_profile"], name="die_profile_excess_idx"),
            models.Index(fields=["alloy"], name="alloy_excess_idx"),
            models.Index(fields=["temper"], name="temper_excess_idx"),
            models.Index(fields=["shift"], name="shift_excess_idx"),
            models.Index(fields=["hardness_value"], name="hardness_value_excess_idx"),
            models.Index(fields=["length"], name="length_excess_idx"),
            models.Index(
                fields=["die_profile", "alloy", "temper"], name="die_alloy_temper_idx"
            ),
            models.Index(
                fields=["bundle_inward", "shift"], name="bundle_shift_excess_idx"
            ),
            models.Index(
                fields=["deleted", "created_at"], name="deleted_created_at_excess_idx"
            ),
            models.Index(fields=["-created_at"], name="created_at_desc_excess_idx"),
        ]
        permissions = [
            ("print_excess_stock_copy", "Can print excess stock"),
            ("download_excess_stock_excel_copy", "Can download excess stock Excel"),
        ]
