# Create your models here.
import uuid

from django.db import models
from common.models import StoreType
from common.models import BaseModel
from settings.models import BaseModule


class Store(BaseModule):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_code = models.CharField(max_length=30, unique=True)
    store_name = models.CharField(max_length=100)
    store_type = models.ForeignKey(
        StoreType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_store_type",
    )
    plant = models.ForeignKey(
        "common.Plant", on_delete=models.PROTECT, related_name="stores"
    )
    allows_negative_stock = models.BooleanField(default=False)

    class Meta:
        db_table = "store"
        ordering = ["store_code"]
        permissions = [
            ("download_store_pdf_copy", "Can download store PDF"),
            ("download_store_excel_copy", "Can download store Excel"),
        ]

    def __str__(self):
        return f"{self.store_code} - {self.store_name}"
