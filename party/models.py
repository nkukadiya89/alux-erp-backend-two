from django.conf import settings
from django.db import models

from common.models import BaseModel

SUNDRY_GROUP = (
    ("sundry_creditors", "sundry_creditors"),
    ("sundry_debtors", "sundry_debtors"),
)


class Party(models.Model):
    name = models.CharField(max_length=150)
    sundry_group = models.CharField(
        max_length=20, choices=SUNDRY_GROUP, default="sundry_debtors"
    )
    account_group = models.CharField(max_length=25)
    customer_category = models.CharField(max_length=25)
    customer_subcategory = models.CharField(max_length=25)
    customer_type = models.CharField(max_length=25)
    office_address = models.TextField(null=True)
    registered_address = models.TextField(null=True)
    shipping_address = models.TextField(null=True)
    applicable_gst = models.CharField(max_length=25, null=True)
    party_section_no = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=25, null=True)
    bank_branch_name = models.CharField(max_length=25, null=True)
    bank_branch_address = models.TextField(null=True)
    bank_account_number = models.CharField(max_length=25, null=True)
    bank_ifsc_code = models.CharField(max_length=15, null=True)
    gst_no = models.CharField(max_length=25, null=True)
    gst_type = models.CharField(max_length=25, null=True)
    pan_number = models.CharField(max_length=15, null=True)
    udhyam_no = models.CharField(max_length=25, null=True)
    sgst_number = models.CharField(max_length=25, null=True)
    cgst_number = models.CharField(max_length=25, null=True)
    unique_id = models.CharField(max_length=64, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="party_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="party_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="party_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "party"

    def __str__(self):
        return f"{self.name} - {self.sundry_group}"
