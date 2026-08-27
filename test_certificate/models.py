from django.db import models
from die.models import Die
from product.models import Alloy, Temper
from settings.models import BaseModule
from bundle_outward.models import BundleOutward


class TestCertificate(BaseModule):
    tc_date = models.DateField(auto_now_add=True)
    tc_no = models.CharField(max_length=30, unique=True)
    bundle_outward = models.ForeignKey(
        BundleOutward,
        on_delete=models.CASCADE,
        related_name="test_certificate_bundle_outward",
        null=True,
        blank=True,
    )
    section_no = models.ForeignKey(
        Die,
        on_delete=models.CASCADE,
        related_name="test_certificate_section_no",
        null=True,
        blank=True,
    )
    length = models.IntegerField(null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True)
    alloy = models.ForeignKey(
        Alloy,
        on_delete=models.CASCADE,
        related_name="test_certificate_alloy",
        null=True,
        blank=True,
    )
    temper = models.ForeignKey(
        Temper,
        on_delete=models.CASCADE,
        related_name="test_certificate_temper",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.tc_no}"

    class Meta:
        db_table = "test_certificate"
        permissions = [
            (
                "download_test_certificate_excel_copy",
                "Can download test certificate Excel",
            ),
            ("download_test_certificate_pdf_copy", "Can download test certificate PDF"),
        ]
