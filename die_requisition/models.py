from django.db import models
from django.utils.timezone import now

from customer.models import Customer
from die.models import DiePress, DieTool
from settings.models import BaseModule
from workorder.models import WorkOrder


class DieRequisition(BaseModule):
    PRIORITY_CHOICES = [("Normal", "Normal"), ("Urgent", "Urgent")]
    STATUS_CHOICES = [
        ("Requested", "Requested"),
        ("Issued", "Issued"),
        ("Rejected", "Rejected"),
        ("Closed", "Closed"),
    ]
    requisition_no = models.CharField(max_length=20, unique=True)
    requisition_date = models.DateField(default=now)
    workorder_no = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="die_requisitions_workorder"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="die_requisition_customer"
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="Normal"
    )
    required_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="Requested"
    )
    remarks = models.TextField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    class Meta:
        permissions = [
            ("can_download_die_requisition_pdf", "Can Download Die Requisition PDF"),
            (
                "can_download_die_requisition_excel",
                "Can Download Die Requisition Excel",
            ),
        ]

    def __str__(self):
        return self.requisition_no


class DieRequisitionDetail(BaseModule):
    CONDITION_CHOICES = [("Ok", "Ok"), ("Repair", "Repair")]
    LOCATION_CHOICES = [
        ("Store", "Store"),
        ("Press", "Press"),
        ("Toolroom", "Toolroom"),
    ]
    APPROVAL_CHOICES = [("Pending", "Pending"), ("Approved", "Approved")]
    requisition = models.ForeignKey(
        DieRequisition, on_delete=models.CASCADE, related_name="die_requisition"
    )
    die_tool = models.ForeignKey(
        DieTool, on_delete=models.CASCADE, related_name="die_requisition_dietool"
    )
    profile_number = models.CharField(max_length=30, null=True, blank=True)
    press = models.ForeignKey(
        DiePress, on_delete=models.CASCADE, related_name="die_requisition_press"
    )
    cavity = models.PositiveIntegerField(default=1)
    location = models.CharField(
        max_length=10, choices=LOCATION_CHOICES, default="Store"
    )
    life_balance = models.IntegerField(null=True, blank=True)
    expected_output_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    actual_qty_produced = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    billets_used = models.IntegerField(null=True, blank=True)
    die_return_date = models.DateField(null=True, blank=True)
    die_condition_after = models.CharField(
        max_length=10, choices=CONDITION_CHOICES, default="Ok"
    )
    approval_status = models.CharField(
        max_length=10, choices=APPROVAL_CHOICES, default="Pending"
    )
    remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.requisition.requisition_no
