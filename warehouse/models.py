from django.conf import settings
from django.db import models

from common.models import BaseModel
from vehicle_master.models import VehicleMaster
from workorder.models import WorkOrder
from settings.models import BaseModule
from shift.models import ShiftSnapshotMixin

class WarehouseBundleInward(BaseModel):
    """Junction table for Warehouse -> BundleInward (finalized bundles)"""

    warehouse = models.ForeignKey(
        "Warehouse", on_delete=models.CASCADE, related_name="warehouse_bundle_inwards"
    )
    bundle_inward = models.ForeignKey(
        "bundle_inward.BundleInward",
        on_delete=models.CASCADE,
        related_name="warehouse_bundle_inwards",
    )

    class Meta:
        db_table = "warehouse_bundle_inward"
        unique_together = ("warehouse", "bundle_inward")


class WarehouseBundleOutward(BaseModel):
    """Junction table for Warehouse -> BundleInward (outward bundles)"""

    warehouse = models.ForeignKey(
        "Warehouse", on_delete=models.CASCADE, related_name="warehouse_bundle_outwards"
    )
    bundle_inward = models.ForeignKey(
        "bundle_inward.BundleInward",
        on_delete=models.CASCADE,
        related_name="warehouse_bundle_outwards",
    )

    class Meta:
        db_table = "warehouse_bundle_outward"
        unique_together = ("warehouse", "bundle_inward")


class Warehouse(BaseModule, ShiftSnapshotMixin):
    workorder = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="warehouse_workorder"
    )
    finalized_bundles = models.ManyToManyField(
        "bundle_inward.BundleInward",
        through="WarehouseBundleInward",
        related_name="finalized_in_warehouses",
        blank=True,
    )
    outward_bundles = models.ManyToManyField(
        "bundle_inward.BundleInward",
        through="WarehouseBundleOutward",
        related_name="outward_in_warehouses",
        blank=True,
    )
    party_name = models.CharField(max_length=50, null=True, blank=True)
    vehicle_no = models.ForeignKey(
        VehicleMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouse_vehicle_no",
    )
    remarks = models.TextField(null=True, blank=True)
    dispatched_to_customer_date = models.DateField(null=True, blank=True)
    approved = models.BooleanField(default=False, null=True)
    dispatched = models.BooleanField(default=False)
    added_for_outword = models.BooleanField(default=False)
    slip_no = models.CharField(max_length=100, null=True, blank=True)
    dispatched_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.workorder} - {self.vehicle_no}"

    class Meta:
        db_table = "warehouse"
        permissions = [
            (
                "print_warehouse_bundle_outward_copy",
                "Can print warehouse bundle outward",
            ),
            (
                "download_warehouse_bundle_outward_excel_copy",
                "Can download warehouse bundle outward Excel",
            ),
            ("print_warehouse_current_stock_copy", "Can print warehouse current stock"),
            (
                "download_warehouse_current_stock_excel_copy",
                "Can download warehouse current stock Excel",
            ),
        ]
