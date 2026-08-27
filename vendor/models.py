from django.conf import settings
from django.db import models
from django.utils.timezone import now

from settings.models import BaseModule
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


class Vendor(BaseModule):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )

    BUSINESS_TYPE = (
        ("INDIAN", "Indian"),
        ("OVERSEAS", "Overseas"),
    )

    person_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=20)

    business_type = models.CharField(
        choices=BUSINESS_TYPE, max_length=15, default="INDIAN"
    )
    import_export_code = models.CharField(max_length=50, blank=True, null=True)
    beneficiary_agent_code = models.CharField(max_length=50, blank=True, null=True)

    udyam_aadhaar_no = models.CharField(max_length=50, null=True)
    udyam_aadhaar_no_verified = models.BooleanField(default=False)

    vendor_registered_name = models.CharField(max_length=100, null=True)
    vendor_trade_name = models.CharField(max_length=100, null=True)
    gst_no = models.CharField(max_length=15, null=True)
    gst_no_verified = models.BooleanField(default=False)
    vendor_code_as_per_company_erp = models.CharField(max_length=30, null=True)
    pan_number = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="PAN Number"
    )
    code = models.CharField(max_length=50, blank=True, null=True)
    fax_number = models.CharField(max_length=15, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    is_active = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)

    registered_business_address_building = models.CharField(max_length=150, null=True)
    registered_business_address_area = models.CharField(max_length=100, null=True)
    registered_business_address_landmark = models.CharField(max_length=100, null=True)
    registered_business_address_pincode = models.CharField(max_length=100, null=True)
    registered_business_address_state = models.CharField(max_length=100, null=True)
    registered_business_address_city = models.CharField(max_length=100, null=True)
    registered_business_address_country = models.CharField(
        max_length=100, blank=True, null=True
    )

    trading_address_building = models.CharField(max_length=150, null=True)
    trading_address_area = models.CharField(max_length=100, null=True)
    trading_address_landmark = models.CharField(max_length=100, null=True)
    trading_address_pincode = models.CharField(max_length=100, null=True)
    trading_address_state = models.CharField(max_length=100, null=True)
    trading_address_city = models.CharField(max_length=100, null=True)
    trading_address_country = models.CharField(max_length=100, blank=True, null=True)

    vendor_logo = models.CharField(max_length=150, null=True)

    def __str__(self):
        return f"{self.person_name} - {self.vendor_registered_name or 'No Vendor Name'}"

    class Meta:
        db_table = "vendor"
        ordering = ["-id"]

        permissions = [
            ("download_vendor_pdf_copy", "Can download vendor PDF"),
            ("download_vendor_excel_copy", "Can download vendor Excel"),
        ]

    def upload_vendor_logo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg"]

        if self.vendor_logo:
            delete_uploaded_file(self.vendor_logo)
        self.vendor_logo, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "MSMEDocument/", self.id, None
        )


class KeyPersons(models.Model):
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="vendor_key_person"
    )
    person_name = models.CharField(max_length=50, null=True)
    designation = models.CharField(max_length=50, null=True)
    email = models.EmailField(null=True)
    contact_number = models.CharField(max_length=15, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="keyperson_vendor_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="keyperson_vendor_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.vendor} - {self.person_name}"

    class Meta:
        db_table = "vendor_key_persons"
        ordering = ["-id"]


class BankDetails(models.Model):
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="vendor_bank_details"
    )
    bank_name = models.CharField(max_length=100, null=True)
    bank_account_number = models.CharField(max_length=50, null=True)
    bank_ifsc_code = models.CharField(max_length=20, null=True)
    branch_address = models.TextField(null=True)
    bank_ad_code = models.CharField(max_length=50, null=True, blank=True)
    beneficiary_swift_code = models.CharField(max_length=50, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_bank_details_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_bank_details_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.vendor} - {self.bank_name}"

    class Meta:
        db_table = "vendor_bank_details"
