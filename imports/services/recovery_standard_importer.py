"""
Recovery Standard bulk importer
"""

import logging
from typing import Dict, List

from django.utils import timezone

from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string
from imports.validators.field_validators import DecimalValidator, StringValidator
from imports.validators.reference_validators import ForeignKeyValidator
from melting_furnace.models import FurnaceType, MaterialType, RecoveryStandard

logger = logging.getLogger(__name__)


class RecoveryStandardImporter(BaseImporter):
    """
    Bulk importer for Recovery Standard module
    """

    MODULE_NAME = "RecoveryStandard"
    REQUIRED_COLUMNS = [
        "Furnace Type",
        "Material Type",
        "Min Recovery",
        "Max Recovery",
        "Standard Loss",
        "Status",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Furnace Type": "furnace_type",
            "Material Type": "material_type",
            "Min Recovery": "min_recovery",
            "Max Recovery": "max_recovery",
            "Standard Loss": "standard_loss",
            "Effective From": "effective_from",  # Date format handling might be needed
            "Status": "status",
            "Remarks": "remarks",
        }

    def get_validators(self) -> Dict[str, List]:
        return {
            "furnace_type": [
                ForeignKeyValidator(
                    "furnace_type",
                    FurnaceType,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "material_type": [
                ForeignKeyValidator(
                    "material_type",
                    MaterialType,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "min_recovery": [
                DecimalValidator(
                    "min_recovery", max_digits=10, decimal_places=2, required=True
                )
            ],
            "max_recovery": [
                DecimalValidator(
                    "max_recovery", max_digits=10, decimal_places=2, required=True
                )
            ],
            "standard_loss": [
                DecimalValidator(
                    "standard_loss", max_digits=10, decimal_places=2, required=True
                )
            ],
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
        field_mapping = self.get_field_mapping()
        transformed = {}
        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        for col_name, field_name in field_mapping.items():
            value = None
            if col_name in row_data:
                value = row_data[col_name]
            elif col_name.strip().lower() in row_data_lower:
                _, value = row_data_lower[col_name.strip().lower()]

            if field_name == "furnace_type":
                if value:
                    name = normalize_string(value)
                    transformed[field_name] = FurnaceType.objects.filter(
                        name__iexact=name
                    ).first()
                else:
                    transformed[field_name] = None
            elif field_name == "material_type":
                if value:
                    key = normalize_string(value)
                    transformed[field_name] = (
                        MaterialType.objects.filter(code__iexact=key).first()
                        or MaterialType.objects.filter(name__iexact=key).first()
                    )
                else:
                    transformed[field_name] = None
            else:
                transformed[field_name] = (
                    normalize_string(value) if isinstance(value, str) else value
                )

        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()

        return transformed

    def create_model_instance(self, validated_data: Dict) -> RecoveryStandard:
        return RecoveryStandard(**validated_data)
