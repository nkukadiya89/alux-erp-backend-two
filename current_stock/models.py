from django.conf import settings
from django.db import models

from customer.models import Customer


class CurrentStock(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="current_stock_customer"
    )
    packed_weight = models.FloatField(default=0.0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currentstok_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currentstok_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currentstok_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.customer} - {self.packed_weight}"

    class Meta:
        db_table = "current_stock"
