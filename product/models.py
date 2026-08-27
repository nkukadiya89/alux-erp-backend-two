import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models

from common.models import UOM, BaseModel, SectionType, YieldUnit

class StandardMaster(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.year}"

class Alloy(models.Model):
    alloy_code = models.CharField(max_length=25, null=True, blank=True)
    standard = models.ForeignKey(StandardMaster, on_delete=models.SET_NULL, null=True, blank=True)
    remark = models.CharField(max_length=250, null=True, blank=True)
    color_code = models.CharField(max_length=50, null=True, blank=True)
    si_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    si_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    mg_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    mg_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    fe_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    fe_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    mn_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    mn_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    cu_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    cu_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    zn_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    zn_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    cr_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    cr_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    ti_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    ti_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    bi_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    bi_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    pb_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    pb_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    sn_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    sn_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    others_each_min = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    others_each_max = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    others_total_min = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    others_total_max = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    al_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    al_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="alloy_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="alloy_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="alloy_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    AL_COMPONENT_MIN_FIELDS = [
        "si_min",
        "mg_min",
        "fe_min",
        "mn_min",
        "cu_min",
        "zn_min",
        "cr_min",
        "ti_min",
        "bi_min",
        "pb_min",
        "sn_min",
        "others_each_min",
        "others_total_min",
    ]
    AL_COMPONENT_MAX_FIELDS = [
        "si_max",
        "mg_max",
        "fe_max",
        "mn_max",
        "cu_max",
        "zn_max",
        "cr_max",
        "ti_max",
        "bi_max",
        "pb_max",
        "sn_max",
        "others_each_max",
        "others_total_max",
    ]

    @classmethod
    def calculate_al_min_max(cls, obj_or_dict):
        """
        Calculate Al Min/Al Max:
        - Al Min = 100 - sum(all *_min fields except al_min)
        - Al Max = 100 - sum(all *_max fields except al_max)
        Important:
        - Empty/NULL values are treated as 0 for summation
        - BUT if ALL Min fields are empty -> al_min remains NULL (not 100)
        - AND if ALL Max fields are empty -> al_max remains NULL (not 100)
        - Result is rounded to 3 decimal places.
        """

        def get_raw(source, field: str):
            return (
                source.get(field)
                if isinstance(source, dict)
                else getattr(source, field, None)
            )

        def has_any_value(fields) -> bool:
            for f in fields:
                v = get_raw(obj_or_dict, f)
                if v is None:
                    continue
                if isinstance(v, str) and v.strip() == "":
                    continue
                return True
            return False

        has_min_values = has_any_value(cls.AL_COMPONENT_MIN_FIELDS)
        has_max_values = has_any_value(cls.AL_COMPONENT_MAX_FIELDS)

        def get_val(source, field: str) -> Decimal:
            if isinstance(source, dict):
                v = source.get(field)
            else:
                v = getattr(source, field, None)
            if v is None or v == "":
                return Decimal("0")
            return v if isinstance(v, Decimal) else Decimal(str(v))

        al_min = None
        al_max = None

        if has_min_values:
            sum_min = sum(
                (get_val(obj_or_dict, f) for f in cls.AL_COMPONENT_MIN_FIELDS),
                Decimal("0"),
            )
            al_min = (Decimal("100") - sum_min).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )

        if has_max_values:
            sum_max = sum(
                (get_val(obj_or_dict, f) for f in cls.AL_COMPONENT_MAX_FIELDS),
                Decimal("0"),
            )
            al_max = (Decimal("100") - sum_max).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )

        return al_min, al_max

    def __str__(self):
        return f"{self.alloy_code} - {self.color_code}"

    class Meta:
        db_table = "alloy"

        permissions = [
            ("download_alloy_pdf_copy", "Can download alloy PDF"),
            ("download_alloy_excel_copy", "Can download alloy Excel"),
        ]


class Temper(models.Model):
    description = models.CharField(max_length=25, null=True, blank=True)
    section_type = models.ForeignKey(
        SectionType, on_delete=models.SET_NULL, null=True, blank=True
    )
    standard = models.ForeignKey(StandardMaster, on_delete=models.SET_NULL, null=True, blank=True)
    alloy = models.ForeignKey(Alloy, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.CharField(max_length=100, null=True, blank=True)
    dimention_unit = models.ForeignKey(
        UOM, on_delete=models.SET_NULL, null=True, blank=True
    )
    elongation_50mm_min = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    elongation_min = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    hardness = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True
    )
    section_thickness_over = models.CharField(max_length=50, null=True, blank=True)
    section_thickness_upto = models.CharField(max_length=50, null=True, blank=True)
    tensile_min = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    tensile_max = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    yield_min = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    yield_max = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    yield_unit = models.ForeignKey(
        YieldUnit, on_delete=models.SET_NULL, null=True, blank=True
    )
    electrical_conductivity_min = models.DecimalField(
        max_digits=5, decimal_places=3, null=True, blank=True
    )
    electrical_conductivity_max = models.DecimalField(
        max_digits=5, decimal_places=3, null=True, blank=True
    )
    temper_code_old = models.CharField(max_length=20, null=True, blank=True)
    temper_code_new = models.CharField(max_length=20, null=True, blank=True)
    heat_treatment = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="temper_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="temper_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="temper_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def clean(self):
        """Validate Temper model constraints"""
        from django.core.exceptions import ValidationError

        if (
            self.section_thickness_over is not None
            and self.section_thickness_upto is not None
            and self.section_thickness_over > self.section_thickness_upto
        ):
            raise ValidationError(
                "Section thickness over cannot be greater than section thickness upto"
            )

        if (
            self.tensile_min is not None
            and self.tensile_max is not None
            and self.tensile_min > self.tensile_max
        ):
            raise ValidationError("Tensile min cannot be greater than tensile max")

        if (
            self.yield_min is not None
            and self.yield_max is not None
            and self.yield_min > self.yield_max
        ):
            raise ValidationError("Yield min cannot be greater than yield max")

        if (
            self.electrical_conductivity_min is not None
            and self.electrical_conductivity_max is not None
            and self.electrical_conductivity_min > self.electrical_conductivity_max
        ):
            raise ValidationError(
                "Electrical conductivity min cannot be greater than electrical conductivity max"
            )

    def __str__(self):
        return f"{self.temper_code_new if self.temper_code_new else None} - {self.alloy.alloy_code if self.alloy else None} - {self.standard.name if self.standard else None}"

    class Meta:
        db_table = "temper"
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'temper_code_new', 'section_type','alloy','dimention_unit', 'yield_unit'],
                condition=models.Q(deleted=False),
                name="unique_active_temper_6_fields",
            )
        ]

        permissions = [
            ("download_temper_pdf_copy", "Can download temper PDF"),
            ("download_temper_excel_copy", "Can download temper Excel"),
        ]


class ItemType(models.Model):
    name = models.CharField(max_length=25, null=True)

    class Meta:
        db_table = "item_type"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class ValuationMethod(models.Model):
    name = models.CharField(max_length=25, null=True)

    class Meta:
        db_table = "valuation_method"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class MaterialCenter(models.Model):
    name = models.CharField(max_length=25, null=True)

    class Meta:
        db_table = "material_center"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Item(BaseModel):
    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    ITEM_TYPES = [
        ("RAW", "Raw Material"),
        ("CONSUMABLE", "Consumable"),
        ("SEMI", "Semi Finished"),
        ("FG", "Finished Good"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_code = models.CharField(max_length=100, unique=True)
    item_name = models.CharField(max_length=255)
    item_type = models.ForeignKey(
        "product.ItemType", related_name="item", on_delete=models.SET_NULL, null=True
    )
    category = models.ForeignKey("common.ItemCategory", on_delete=models.CASCADE)
    uom = models.ForeignKey("common.UOM", related_name="uom", on_delete=models.CASCADE)
    alloy_code = models.CharField(max_length=50, null=True, blank=True)
    heat_tracking = models.BooleanField(default=False)
    reorder_level = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    hsn_code = models.CharField(max_length=10, null=True)
    gst_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    base_unit = models.CharField(max_length=10, default="KG")
    net_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Weight per piece or per batch in KG",
        default=Decimal("0.00"),
    )
    purchase_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.000")
    )
    sale_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    valuation_method = models.ForeignKey(
        "product.ValuationMethod",
        related_name="item",
        on_delete=models.SET_NULL,
        null=True,
    )
    minimum_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    maximum_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.00")
    )
    reorder_qty = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    making_time_minutes = models.PositiveIntegerField(
        help_text="Extrusion or manufacturing time per job", default=0
    )
    lead_time_days = models.PositiveIntegerField(default=0)
    bom_required = models.BooleanField(default=False)
    material_center = models.ForeignKey(
        "product.MaterialCenter",
        related_name="item",
        on_delete=models.SET_NULL,
        null=True,
    )
    batch_managed = models.BooleanField(default=True)
    grn_required = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="item_deleted",
    )

    class Meta:
        db_table = "item"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item_code} - {self.item_name}"
