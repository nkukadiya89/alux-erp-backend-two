from django.conf import settings
from django.db import models

from customer.models import Customer
from die.models import Die
from product.models import Alloy, Temper


class DieQuotation(models.Model):
    MINIMUM_ORDER_QTY_CHOICES = (
        ("<300", "<300"),
        ("300 - 500", "300 - 500"),
        (">500", ">500"),
    )

    DIE_RIGHT_CHOICES = (
        ("Own", "Own"),
        ("Customer", "Customer"),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="die_quotation_customer",
        null=True,
    )
    minimum_order_qty = models.CharField(
        max_length=250, choices=MINIMUM_ORDER_QTY_CHOICES, default="<300"
    )
    die_right = models.CharField(
        max_length=250, choices=DIE_RIGHT_CHOICES, default="Own"
    )
    sample_delivery = models.CharField(max_length=250, null=True, blank=True)
    terms_and_condition = models.TextField(null=True, blank=True)
    quotation_date = models.DateTimeField(auto_now=True)
    die_quotation_no = models.CharField(max_length=100, null=True, blank=True)
    inquiry_base_number = models.CharField(max_length=10, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diequotation_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diequotation_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diequotation_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.customer} - {self.minimum_order_qty}"

    class Meta:
        db_table = "die_quotation"
        indexes = [
            models.Index(fields=["-id", "deleted"]),
            models.Index(fields=["customer", "deleted"]),
            models.Index(fields=["die_quotation_no"]),
            models.Index(fields=["quotation_date", "deleted"]),
        ]
        permissions = [
            ("print_die_quotation_pdf_copy", "Can print die quotation"),
            (
                "download_die_quotation_excel_copy",
                "Can download die quotation Excel",
            ),
        ]


class DieQuotationDetails(models.Model):
    die_quotation = models.ForeignKey(
        DieQuotation,
        on_delete=models.CASCADE,
        related_name="die_quotation_details_die_quotation",
        null=True,
    )
    profile_no = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="die_quotation_details_die",
        null=True,
    )
    customer_reference_no = models.CharField(max_length=250, null=True, blank=True)
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        null=True,
        related_name="die_quotation_details_alloy",
    )
    temper = models.ForeignKey(
        Temper, 
        on_delete=models.CASCADE,
        null=True,
        related_name="die_quotation_details_temper",
    )
    press_capacity = models.CharField(max_length=250, null=True, blank=True)
    quantity = models.CharField(max_length=250, null=True, blank=True)
    unit_of_measurement = models.CharField(max_length=25, null=True, blank=True)
    profile_devlopment_cost = models.FloatField(max_length=250, null=True, blank=True)
    inquiry_number = models.CharField(max_length=20, null=True, blank=True, unique=True)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conversion = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diequotationdetail_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diequotationdetail_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diequotationdetail_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.die_quotation} - {self.customer_reference_no}"

    class Meta:
        db_table = "die_quotation_details"
        indexes = [
            models.Index(fields=["die_quotation", "deleted"]),
            models.Index(fields=["inquiry_number"]),
        ]
