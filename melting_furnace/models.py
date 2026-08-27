from django.conf import settings
from django.db import models

from common.models import UOM, BaseModel


class MaterialType(models.Model):
    code = models.CharField(
        "Code",
        max_length=10,
        unique=True,
        db_index=True,
    )
    name = models.CharField("Name", max_length=100)
    description = models.TextField("Description", blank=True, null=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "material_type"
        ordering = ["name"]
        verbose_name = "Material Type"
        verbose_name_plural = "Material Types"


class FurnaceType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class FuelType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Furnace(BaseModel):
    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    )

    furnace_code = models.CharField(max_length=100)
    furnace_name = models.CharField(max_length=150)
    furnace_type = models.ForeignKey(FurnaceType, on_delete=models.CASCADE)
    furnace_capacity = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_type = models.ForeignKey(FuelType, on_delete=models.CASCADE)
    min_temperature = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_temperature = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Active", db_index=True
    )
    remark = models.TextField(null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="furnace_deleted",
    )
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.furnace_name

    is_archived = models.BooleanField(default=False)

    class Meta:
        db_table = "furnace"
        ordering = ["-id"]
        permissions = [
            ("download_furnace_pdf_copy", "Can download furnace PDF"),
            ("download_furnace_excel_copy", "Can download furnace Excel"),
        ]


class AdditiveCategory(BaseModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class AdditiveMaster(BaseModel):
    additive_code = models.CharField(max_length=100)
    additive_name = models.CharField(max_length=150)
    category = models.ForeignKey(AdditiveCategory, on_delete=models.CASCADE, null=True)
    unit = models.ForeignKey(UOM, on_delete=models.CASCADE, null=True)
    standard_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    min_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    status = models.CharField(max_length=20)
    remarks = models.TextField(null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="additive_master_deleted",
    )
    deleted_at = models.DateTimeField(null=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return self.additive_name

    class Meta:
        ordering = ["-id"]
        permissions = [
            ("download_additive_master_pdf_copy", "Can download additive_master PDF"),
            (
                "download_additive_master_excel_copy",
                "Can download additive_master Excel",
            ),
        ]


class RecoveryStandard(BaseModel):
    furnace_type = models.ForeignKey(
        FurnaceType,
        on_delete=models.CASCADE,
        related_name="recovery_standards",
    )
    material_type = models.ForeignKey(
        MaterialType,
        on_delete=models.PROTECT,
        related_name="recovery_standards",
    )
    min_recovery = models.DecimalField(max_digits=10, decimal_places=2)
    max_recovery = models.DecimalField(max_digits=10, decimal_places=2)
    standard_loss = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField(null=True)
    status = models.CharField(max_length=20)
    remarks = models.TextField(null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recovery_standard_deleted",
    )
    deleted_at = models.DateTimeField(null=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.furnace_type} - {self.material_type}"

    class Meta:
        ordering = ["-id"]
        permissions = [
            (
                "download_recovery_standard_pdf_copy",
                "Can download recovery_standard PDF",
            ),
            (
                "download_recovery_standard_excel_copy",
                "Can download recovery_standard Excel",
            ),
        ]
