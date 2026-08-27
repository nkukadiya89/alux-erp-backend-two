"""
Furnace Master bulk importer
"""

import logging
from typing import Dict, List

from django.utils import timezone

from imports.services.base_importer import BaseImporter
from imports.utils import normalize_choice, normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    DecimalValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import ForeignKeyValidator
from melting_furnace.models import FuelType, Furnace, FurnaceType

logger = logging.getLogger(__name__)


class FurnaceImporter(BaseImporter):
    """
    Bulk importer for Furnace Master module
    """

    MODULE_NAME = "Furnace"
    REQUIRED_COLUMNS = [
        "Furnace Code",
        "Furnace Name",
        "Furnace Type",
        "Fuel Type",
        "Furnace Capacity",
        "Status",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_furnace_codes = set()  # Track furnace codes for uniqueness

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.
        """
        return {
            "Furnace Code": "furnace_code",
            "Furnace Name": "furnace_name",
            "Furnace Type": "furnace_type",
            "Fuel Type": "fuel_type",
            "Furnace Capacity": "furnace_capacity",
            "Min Temperature": "min_temperature",
            "Max Temperature": "max_temperature",
            "Status": "status",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.
        """
        return {
            "furnace_code": [
                UniqueValidator("furnace_code", self.seen_furnace_codes, required=True),
                StringValidator("furnace_code", max_length=100, required=True),
            ],
            "furnace_name": [
                StringValidator("furnace_name", max_length=150, required=True)
            ],
            "furnace_type": [
                ForeignKeyValidator(
                    "furnace_type",
                    FurnaceType,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "fuel_type": [
                ForeignKeyValidator(
                    "fuel_type",
                    FuelType,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "furnace_capacity": [
                DecimalValidator(
                    "furnace_capacity", max_digits=10, decimal_places=2, required=True
                )
            ],
            "min_temperature": [
                DecimalValidator(
                    "min_temperature", max_digits=10, decimal_places=2, required=False
                )
            ],
            "max_temperature": [
                DecimalValidator(
                    "max_temperature", max_digits=10, decimal_places=2, required=False
                )
            ],
            "status": [
                StringValidator("status", max_length=20, required=True)
                # Note: status is CharField in model, not choices.
                # If there are choices, use ChoiceValidator.
                # Department used ChoiceValidator. Furnace model has status as CharField(20).
                # Assuming "Active"/"Inactive" convention.
            ],
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.
        """
        field_mapping = self.get_field_mapping()
        transformed = {}

        # Create case-insensitive lookup
        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        validators = self.get_validators()

        # Map and normalize values
        for col_name, field_name in field_mapping.items():
            value = None
            if col_name in row_data:
                value = row_data[col_name]
            else:
                col_name_lower = col_name.strip().lower()
                if col_name_lower in row_data_lower:
                    original_key, value = row_data_lower[col_name_lower]

            # Apply transformations
            if field_name == "furnace_code":
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "furnace_type":
                # FK lookup handled by validator or pre-processing?
                # BaseImporter validators usually handle validation, but transformation to ID happens here or in create?
                # DepartmentImporter handled FK lookup in transform_row_data.
                if value:
                    name = normalize_string(value)
                    try:
                        instance = FurnaceType.objects.filter(name__iexact=name).first()
                        transformed[field_name] = instance
                        if not instance:
                            logger.warning(f"FurnaceType '{name}' not found")
                    except Exception:
                        transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name == "fuel_type":
                if value:
                    name = normalize_string(value)
                    try:
                        instance = FuelType.objects.filter(name__iexact=name).first()
                        transformed[field_name] = instance
                        if not instance:
                            logger.warning(f"FuelType '{name}' not found")
                    except Exception:
                        transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name in [
                "furnace_capacity",
                "min_temperature",
                "max_temperature",
            ]:
                # Decimals handled by serializer/create usually, but here we prepare for model
                transformed[field_name] = value
            else:
                transformed[field_name] = normalize_string(value)

        # Add audit fields
        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()

        return transformed

    def create_model_instance(self, validated_data: Dict) -> Furnace:
        """
        Create Furnace model instance from validated data.
        """
        # Exclude None values for optional fields if needed, OR model handles them.
        # Model has null=True for min/max temp.
        return Furnace(**validated_data)
