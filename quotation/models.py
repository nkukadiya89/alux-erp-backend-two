from django.conf import settings
from django.db import models

from common.models import JobWorkType, PackingMode
from customer.models import Customer
from die.models import Die
from product.models import Alloy, Temper


class Quotation(models.Model):
    STATUS_CHOICE = (
        ("Quotation", "Quotation"),
        ("WorkOrder", "WorkOrder"),
    )

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="quotation_customer", null=True
    )
    packing_mode = models.ManyToManyField(
        PackingMode,
        related_name="quotation_packing_modes",
        blank=True,
    )
    quotation_date = models.DateField(auto_now=True)
    project_name = models.CharField(max_length=100, null=True, blank=True)
    terms_and_condition = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    quotation_no = models.CharField(max_length=100, null=True, blank=True)

    converted_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        choices=STATUS_CHOICE, default="Quotation", max_length=100
    )
    workorder_no = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quotation_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quotation_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quotation_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.customer} - {self.project_name}"

    class Meta:
        db_table = "quotation"
        indexes = [
            models.Index(fields=["-created_at", "deleted"]),
            models.Index(fields=["customer", "deleted"]),
            models.Index(fields=["status", "deleted"]),
            models.Index(fields=["quotation_no"]),
        ]
        permissions = [
            ("print_quotation_pdf_copy", "Can print quotation"),
            (
                "download_quotation_excel_copy",
                "Can download quotation Excel",
            ),
        ]


class QuotationDetail(models.Model):
    RATE_PER_CHOICE = (
        ("Kg", "Kg"),
        ("RMT", "RMT"),
        ("Piece", "Piece"),
    )

    JOBWORK_CHOICE = (
        ("Mill Finish", "Mill Finish"),
        ("Engineering", "Engineering"),
        ("Surface treatment", "Surface treatment"),
        ("Out Source", "Out Source"),
        ("Laser marking", "Laser marking"),
        ("Thermal Brea", "Thermal Brea"),
    )

    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name="quotation_quotation_detail"
    )
    die_profile = models.ForeignKey(
        Die, on_delete=models.CASCADE, null=True, related_name="quotation_die_profile"
    )
    alloy = models.ForeignKey(
        Alloy, on_delete=models.CASCADE, null=True, related_name="quotation_alloy"
    )
    temper = models.ForeignKey(
        Temper, on_delete=models.CASCADE, null=True, related_name="quotation_temper"
    )
    customer_reference_no = models.CharField(max_length=100, null=True, blank=True)
    length = models.IntegerField(default=0, null=True, blank=True)
    pieces = models.IntegerField(default=0, null=True, blank=True)
    net_weight = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )

    jobworks = models.ManyToManyField(
        JobWorkType, related_name="quotation_details", blank=True
    )

    out_source = models.BooleanField(default=False, null=True, blank=True)

    laser_marking_description = models.CharField(max_length=250, null=True, blank=True)
    laser_marking_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )

    cutting = models.BooleanField(default=False, null=True, blank=True)
    machining = models.BooleanField(default=False, null=True, blank=True)
    deburring = models.BooleanField(default=False, null=True, blank=True)

    cutting_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    machining_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    deburring_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )

    anodising = models.BooleanField(default=False, null=True, blank=True)
    powder_coating = models.BooleanField(default=False, null=True, blank=True)
    pvdf = models.BooleanField(default=False, null=True, blank=True)

    anodising_description = models.CharField(max_length=250, null=True, blank=True)
    anodising_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )

    powder_coating_description = models.CharField(max_length=250, null=True, blank=True)
    powder_coating_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )

    pvdf_description = models.CharField(max_length=250, null=True, blank=True)
    pvdf_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    unit_of_measurement = models.CharField(
        choices=RATE_PER_CHOICE, max_length=25, null=True
    )
    price_per_kg = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    description = models.CharField(max_length=250, null=True, blank=True)
    conversion = models.CharField(max_length=250, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quotationdetail_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quotationdetail_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quotationdetail_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.quotation} - {self.net_weight}"

    class Meta:
        db_table = "quotation_detail"
        indexes = [
            models.Index(fields=["quotation", "deleted"]),
        ]
