from django.db import models

from common.models import JobWorkType, PackingMode
from customer.models import Customer
from die.models import Die
from product.models import Alloy, Temper
from settings.models import BaseModule
from workorder.models import WorkOrder


class Proforma(BaseModule):
    PROFORMA_STATUS_CHOICES = (
        ("NORMAL", "NORMAL"),
        ("WORKORDER", "WORKORDER"),
    )
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="proforma_workorder",
        db_index=True,
        null=True,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="proforma_customer",
        null=True,
        db_index=True,
    )
    workorder_no = models.CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    packing_mode = models.ManyToManyField(
        PackingMode, related_name="proforma_packing_mode", blank=True
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
    delivery_schedule = models.CharField(max_length=100, null=True, blank=True)
    weight_range = models.CharField(max_length=100, null=True, blank=True)
    type = models.CharField(
        max_length=20, choices=PROFORMA_STATUS_CHOICES, default="WORKORDER"
    )
    remarks = models.TextField(null=True, blank=True)
    proforma_no = models.CharField(
        max_length=100, null=True, blank=True, unique=True, db_index=True
    )

    def __str__(self):
        return f"{self.workorder} - {self.proforma_date}"

    class Meta:
        db_table = "proforma"
        indexes = [
            models.Index(fields=["workorder"], name="workorder_proforma_idx"),
            models.Index(fields=["customer"], name="customer_proforma_idx"),
            models.Index(fields=["proforma_no"], name="proforma_no_idx"),
            models.Index(fields=["workorder_no"], name="workorder_no_proforma_idx"),
            models.Index(fields=["proforma_date"], name="proforma_date_idx"),
            models.Index(
                fields=["workorder", "proforma_date"],
                name="workorder_date_proforma_idx",
            ),
            models.Index(
                fields=["customer", "proforma_date"], name="customer_date_proforma_idx"
            ),
            models.Index(fields=["deleted", "created_at"], name="pf_del_cr_idx"),
            models.Index(fields=["deleted", "deleted_at"], name="pf_del_del_idx"),
            models.Index(fields=["created_by", "created_at"], name="pf_crby_crat_idx"),
            models.Index(fields=["-created_at"], name="created_at_desc_proforma_idx"),
            models.Index(fields=["-proforma_date"], name="proforma_date_desc_idx"),
        ]
        permissions = [
            ("print_proforma_copy", "Can print proforma copy"),
            ("print_proforma_pdf_copy", "Can print die quotation"),
            (
                "download_proforma_excel_copy",
                "Can download proforma Excel",
            ),
        ]


class ProformaDetails(BaseModule):
    proforma = models.ForeignKey(
        Proforma,
        on_delete=models.CASCADE,
        related_name="proforma_details_proforma",
        db_index=True,
    )
    profile_no = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="proforma_detail_die",
        null=True,
        db_index=True,
    )
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        related_name="proforma_detail_alloy",
        null=True,
        db_index=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="proforma_detail_temper",
        null=True,
        db_index=True,
    )
    customer_reference_no = models.CharField(
        max_length=250, null=True, blank=True, db_index=True
    )

    jobworks = models.ManyToManyField(
        JobWorkType, related_name="proforma_details", blank=True
    )
    description = models.TextField(null=True, blank=True)
    out_source = models.BooleanField(default=False, null=True, db_index=True)
    laser_marking_description = models.CharField(max_length=250, null=True)
    laser_marking_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True
    )
    cutting = models.BooleanField(default=False, null=True, db_index=True)
    machining = models.BooleanField(default=False, null=True, db_index=True)
    deburring = models.BooleanField(default=False, null=True, db_index=True)

    cutting_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    machining_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    deburring_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)

    anodising = models.BooleanField(default=False, null=True, db_index=True)
    powder_coating = models.BooleanField(default=False, null=True, db_index=True)
    pvdf = models.BooleanField(default=False, null=True, db_index=True)

    anodising_description = models.CharField(max_length=250, null=True)
    anodising_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)

    powder_coating_description = models.CharField(max_length=250, null=True)
    powder_coating_price = models.DecimalField(
        decimal_places=2, max_digits=10, null=True
    )

    pvdf_description = models.CharField(max_length=250, null=True)
    pvdf_price = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    length = models.DecimalField(decimal_places=2, max_digits=10)
    pieces = models.IntegerField(default=0, null=True, db_index=True)
    net_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    nalco_rate = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    packed_weight = models.DecimalField(decimal_places=3, max_digits=10, null=True)
    dispatch_qty = models.FloatField(default=0.0, null=True, db_index=True)
    conversion = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)

    def __str__(self):
        return f"{self.proforma} - {self.customer_reference_no}"

    class Meta:
        db_table = "proforma_details"
        indexes = [
            models.Index(fields=["proforma"], name="proforma_details_proforma_idx"),
            models.Index(fields=["profile_no"], name="profile_no_idx"),
            models.Index(fields=["alloy"], name="alloy_details_idx"),
            models.Index(fields=["temper"], name="temper_details_idx"),
            models.Index(fields=["customer_reference_no"], name="customer_ref_no_idx"),
            models.Index(fields=["out_source"], name="out_source_idx"),
            models.Index(fields=["cutting"], name="cutting_idx"),
            models.Index(fields=["machining"], name="machining_idx"),
            models.Index(fields=["deburring"], name="deburring_idx"),
            models.Index(fields=["anodising"], name="anodising_idx"),
            models.Index(fields=["powder_coating"], name="powder_coating_idx"),
            models.Index(fields=["pvdf"], name="pvdf_idx"),
            models.Index(fields=["pieces"], name="pieces_details_idx"),
            models.Index(fields=["dispatch_qty"], name="dispatch_qty_idx"),
            models.Index(fields=["proforma", "profile_no"], name="proforma_die_idx"),
            models.Index(
                fields=["proforma", "alloy", "temper"], name="proforma_alloy_temper_idx"
            ),
            models.Index(
                fields=["profile_no", "alloy", "temper"], name="pfdet_die_alloy_tmp_idx"
            ),
            models.Index(
                fields=["out_source", "cutting", "machining"], name="jobwork_flags_idx"
            ),
            models.Index(
                fields=["anodising", "powder_coating", "pvdf"],
                name="finishing_flags_idx",
            ),
            models.Index(
                fields=["deleted", "created_at"], name="deleted_created_at_details_idx"
            ),
            models.Index(fields=["-created_at"], name="created_at_desc_details_idx"),
        ]
