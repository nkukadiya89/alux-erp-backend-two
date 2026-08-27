from django.db import models
from settings.models import BaseModule
from customer.models import Customer
from product.models import Alloy, Temper

class DieProforma(BaseModule):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="die_proforma_customer",
        null=True,
        db_index=True,
    )
    freight_charges = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    advance_amount = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    transport_charges = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    insurance_charges = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    other_charges = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    proforma_date = models.DateField(auto_now=True, db_index=True)
    terms_and_condition = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    proforma_no = models.CharField(
        max_length=100, null=True, blank=True, unique=True, db_index=True
    )
    purchase_order_no = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    purchase_order_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer} - {self.proforma_date}"

    class Meta:
        db_table = "die_proforma"
        permissions = [
            ("print_die_proforma_copy", "Can print die proforma copy"),
            ("download_proforma_pdf_copy", "Can download proforma Pdf copy"),
            ("download_proforma_excel_copy", "Can download proforma Excel copy"),
        ]



class DieProformaDetails(BaseModule):
    die_proforma = models.ForeignKey(
        DieProforma,
        on_delete=models.CASCADE,
        related_name="die_proforma_details_proforma",
        db_index=True,
    )
    pieces = models.IntegerField(default=0, null=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    hsn = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    quantity = models.IntegerField(null=True, db_index=True)
    rate = models.DecimalField(decimal_places=2, max_digits=10, null=True, db_index=True)

    def __str__(self):
        return f"{self.die_proforma} - {self.rate}"

    class Meta:
        db_table = "die_proforma_detail"