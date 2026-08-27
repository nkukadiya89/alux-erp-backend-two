from django.db import models

from common.models import BaseModel


class StockVerification(BaseModel):
    verified_bundles = models.TextField(null=True)
    unverified_bundles = models.TextField(null=True)

    class Meta:
        db_table = "stock_verification"
        permissions = [
            ("print_stock_verification_copy", "Can print stock verification"),
            ("print_dispatch_verification_copy", "Can print dispatch verification"),
        ]
