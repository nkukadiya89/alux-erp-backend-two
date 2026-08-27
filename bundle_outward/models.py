from django.db import models

from common.models import BaseModel
from customer.models import Customer
from settings.models import BaseModule
from vehicle_master.models import VehicleMaster
from workorder.models import WorkOrder
from shift.models import ShiftSnapshotMixin

class BundleOutwardInward(BaseModel):
    """Junction table for BundleOutward -> BundleInward (finalized bundles)"""

    bundle_outward = models.ForeignKey(
        "BundleOutward", on_delete=models.CASCADE, related_name="bundle_outward_inwards"
    )
    bundle_inward = models.ForeignKey(
        "bundle_inward.BundleInward",
        on_delete=models.CASCADE,
        related_name="bundle_outward_inwards",
    )

    class Meta:
        db_table = "bundle_outward_inward"
        unique_together = ("bundle_outward", "bundle_inward")


class BundleOutwardOutward(BaseModel):
    """Junction table for BundleOutward -> BundleInward (outward bundles)"""

    bundle_outward = models.ForeignKey(
        "BundleOutward",
        on_delete=models.CASCADE,
        related_name="bundle_outward_outwards",
    )
    bundle_inward = models.ForeignKey(
        "bundle_inward.BundleInward",
        on_delete=models.CASCADE,
        related_name="bundle_outward_outwards",
    )

    class Meta:
        db_table = "bundle_outward_outward"
        unique_together = ("bundle_outward", "bundle_inward")


class BundleOutward(BaseModule, ShiftSnapshotMixin):
    DISPATCH_TO_CHOICES = (
        ("Warehouse", "Warehouse"),
        ("Customer", "Customer"),
    )

    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="bundle_outward_workorder",
        db_index=True,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="bundle_outward_customer",
        null=True,
        db_index=True,
    )
    finalized_bundles = models.ManyToManyField(
        "bundle_inward.BundleInward",
        through="BundleOutwardInward",
        related_name="finalized_in_bundle_outwards",
        blank=True,
    )
    outward_bundles = models.ManyToManyField(
        "bundle_inward.BundleInward",
        through="BundleOutwardOutward",
        related_name="outward_in_bundle_outwards",
        blank=True,
    )

    slip_no = models.CharField(max_length=100, null=True, db_index=True)
    date_prepared = models.DateTimeField(auto_now=True, null=True, db_index=True)
    dispatch_to = models.CharField(
        choices=DISPATCH_TO_CHOICES,
        default="Warehouse",
        max_length=100,
        null=True,
        db_index=True,
    )
    vehicle_no = models.ForeignKey(
        VehicleMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bundle_outword_vehicle_no",
        db_index=True,
    )
    party_name = models.CharField(max_length=50, null=True, blank=True)
    approved = models.BooleanField(default=False, null=True, db_index=True)
    remarks = models.TextField(null=True)
    dispatch_date = models.DateTimeField(null=True, db_index=True)

    def __str__(self):
        return f"{self.workorder} - {self.slip_no}"

    class Meta:
        db_table = "bundle_outward"
        permissions = [
            ("print_bundle_outward_copy", "Can print bundle outward"),
            ("download_bundle_outward_excel_copy", "Can download bundle outward Excel"),
            ("print_dispatch_report_copy", "Can print dispatch report"),
            (
                "download_dispatch_report_excel_copy",
                "Can download dispatch report Excel",
            ),
        ]
        indexes = [
            models.Index(
                fields=["customer", "dispatch_to"], name="idx_customer_dispatch_to"
            ),
            models.Index(fields=["slip_no"], name="idx_slip_no"),
            models.Index(
                fields=["approved", "dispatch_date"], name="idx_approved_dispatch_date"
            ),
        ]
