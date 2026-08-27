from django.conf import settings
from django.db import models


class NalcoMaster(models.Model):
    ADJUSTMENT_CHOICES = (
        ("Increase", "Increase"),
        ("Decrease", "Decrease"),
    )
    date = models.DateField()
    ignot_grade = models.CharField(max_length=100)
    rate_per_mt = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Rate / MT"
    )
    rate_per_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Rate / KG"
    )
    adjustment_type = models.CharField(
        max_length=20, choices=ADJUSTMENT_CHOICES, null=True, blank=True
    )
    adjustment_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    final_rate_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    final_rate_mt = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    diff_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    diff_mt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    percentage_change = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="nalcomaster_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="nalcomaster_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="nalcomaster_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.ignot_grade} - {self.rate_per_mt}"

    class Meta:
        permissions = [
            ("download_nalco_rate_pdf_copy", "Can download nalco rate PDF"),
            ("download_nalco_rate_excel_copy", "Can download nalco rate Excel"),
        ]
