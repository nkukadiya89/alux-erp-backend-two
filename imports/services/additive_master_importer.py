"""
Additive Master bulk importer
"""

import logging
from typing import Dict, List

from django.utils import timezone

from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    DecimalValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import ForeignKeyValidator
from melting_furnace.models import UOM, AdditiveCategory, AdditiveMaster

logger = logging.getLogger(__name__)


class AdditiveMasterImporter(BaseImporter):
    """
    Bulk importer for Additive Master module
    """

    MODULE_NAME = "AdditiveMaster"
    REQUIRED_COLUMNS = [
        "Additive Code",
        "Additive Name",
        "Category",
        "Unit",
        "Status",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_codes = set()

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Additive Code": "additive_code",
            "Additive Name": "additive_name",
            "Category": "category",
            "Unit": "unit",
            "Standard Quantity": "standard_quantity",
            "Min Limit": "min_limit",
            "Max Limit": "max_limit",
            "Status": "status",
            "Remarks": "remarks",
        }

    def get_validators(self) -> Dict[str, List]:
        return {
            "additive_code": [
                UniqueValidator("additive_code", self.seen_codes, required=True),
                StringValidator("additive_code", max_length=100, required=True),
            ],
            "additive_name": [
                StringValidator("additive_name", max_length=150, required=True)
            ],
            "category": [
                ForeignKeyValidator(
                    "category",
                    AdditiveCategory,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "unit": [
                ForeignKeyValidator(
                    "unit",
                    UOM,
                    lookup_field="name",  # Assuming UOM has name
                    required=True,
                    case_sensitive=False,
                )
            ],
            "status": [StringValidator("status", max_length=20, required=True)],
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

            if field_name == "additive_code":
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "category":
                if value:
                    name = normalize_string(value)
                    transformed[field_name] = AdditiveCategory.objects.filter(
                        name__iexact=name
                    ).first()
                else:
                    transformed[field_name] = None
            elif field_name == "unit":
                if value:
                    name = normalize_string(value)
                    transformed[field_name] = UOM.objects.filter(
                        name__iexact=name
                    ).first()
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

    def create_model_instance(self, validated_data: Dict) -> AdditiveMaster:
        return AdditiveMaster(**validated_data)
