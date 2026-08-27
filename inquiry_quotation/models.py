from django.conf import settings
from django.db import models

from common.models import JobWorkType
from inquiry.models import Inquiry
from product.models import Alloy, Temper


class InquiryQuotation(models.Model):
    STATUS_CHOICES = (
        ("Quotation", "Quotation"),
        ("WorkOrder", "WorkOrder"),
        ("SalesOrder", "SalesOrder"),
    )
    inquiry = models.ForeignKey(
        Inquiry, on_delete=models.CASCADE, related_name="inquiry_quotations", db_index=True
    )
    quotation_no = models.CharField(max_length=100, null=True, blank=True)
    revision_number = models.IntegerField(default=0)
    quotation_date = models.DateField(auto_now=True)
    terms_and_condition = models.TextField(null=True, blank=True)
    status = models.CharField(
        choices=STATUS_CHOICES, default="Quotation", max_length=100
    )
    remarks = models.TextField(null=True, blank=True)
    converted_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_quotation_created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_quotation_updated_by",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_quotation_deleted_by",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.quotation_no or f"Quotation {self.id}"

    class Meta:
        db_table = "inquiry_quotation"
        constraints = [
            models.UniqueConstraint(
                fields=["quotation_no", "revision_number"],
                name="unique_quotation_revision",
            )
        ]
        indexes = [
        models.Index(
            fields=["quotation_no", "revision_number"],
            name="iq_quote_rev_idx",
        ),
        ]
        permissions = [
            ("print_inquiry_quotation_pdf_copy", "Can print inquiry quotation"),
            (
                "download_inquiry_quotation_excel_copy",
                "Can download inquiry quotation Excel",
            ),
            (
                "download_inquiry_quotation_pdf_copy",
                "Can download inquiry quotation PDF",
            ),
        ]


class InquiryQuotationDetail(models.Model):
    inquiry_quotation = models.ForeignKey(
        InquiryQuotation,
        on_delete=models.CASCADE,
        related_name="inquiry_quotation_details",
        db_index=True
    )
    section_no = models.CharField(max_length=100, null=True, blank=True)
    alloy = models.ForeignKey(Alloy, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    temper = models.ForeignKey(Temper, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    length = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    price_per_kg = models.DecimalField(
        default=0.0, decimal_places=3, max_digits=10, null=True, blank=True
    )
    conversion = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    packing_cost = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    net_weight = models.DecimalField(
        default=0.0, decimal_places=3, max_digits=10, null=True, blank=True
    )
    quantity = models.IntegerField(default=0, null=True, blank=True)
    surface_finish = models.ManyToManyField(
        JobWorkType,
        related_name="inquiry_quotation_surface_finish",
        blank=True,
    )
    out_source = models.BooleanField(default=False, null=True)
    cutting = models.BooleanField(default=False, null=True)
    machining = models.BooleanField(default=False, null=True)
    deburring = models.BooleanField(default=False, null=True)
    cutting_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    machining_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    deburring_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    anodising = models.BooleanField(default=False, null=True)
    powder_coating = models.BooleanField(default=False, null=True)
    pvdf = models.BooleanField(default=False, null=True)
    anodising_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    anodising_description = models.CharField(max_length=250, null=True)
    powder_coating_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    powder_coating_description = models.CharField(max_length=250, null=True)
    pvdf_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    pvdf_description = models.CharField(max_length=250, null=True)
    laser_marking_price = models.DecimalField(
        decimal_places=3, max_digits=10, null=True, blank=True
    )
    laser_marking_description = models.CharField(max_length=250, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_quotation_detail_created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_quotation_detail_updated_by",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inquiry_quotation_detail_deleted_by",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Detail for {self.inquiry_quotation}"

    class Meta:
        db_table = "inquiry_quotation_detail"
        permissions = [
            (
                "download_inquiry_quotation_detail_excel_copy",
                "Can download inquiry quotation detail Excel",
            ),
            (
                "download_inquiry_quotation_detail_pdf_copy",
                "Can download inquiry quotation detail PDF",
            ),
        ]
