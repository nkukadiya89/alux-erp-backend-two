from django.conf import settings
from django.db import models

from settings.models import BaseModule


class Material(BaseModule):
    material_name = models.CharField(max_length=200, null=True, blank=True, unique=True)

    def __str__(self):
        return self.material_name

    class Meta:
        db_table = "material"

        permissions = [
            ("download_material_excel_copy", "Can download material Excel"),
            ("download_material_pdf_copy", "Can download material PDF"),
        ]
