"""
Store Master bulk importer
"""

import logging
from typing import Dict, List

from django.utils import timezone

from common.models import Plant
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_choice, normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import ForeignKeyValidator
from store.models import Store

logger = logging.getLogger(__name__)


class StoreImporter(BaseImporter):
    """
    Bulk importer for Store Master module
    """

    MODULE_NAME = "Store"
    REQUIRED_COLUMNS = [
        "Store Code",
        "Store Name",
        "Store Type",
        "Plant Code",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_store_codes = set()  # Track store codes for uniqueness
        self.plant_cache = {}  # Cache Plant lookups by plant_code

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Store Code": "store_code",
            "Store Name": "store_name",
            "Store Type": "store_type",
            "Plant Code": "plant",
            "Allows Negative Stock": "allows_negative_stock",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "store_code": [
                UniqueValidator("store_code", self.seen_store_codes, required=True),
                StringValidator("store_code", max_length=30, required=True),
            ],
            "store_name": [
                StringValidator("store_name", max_length=100, required=True),
            ],
            "store_type": [
                ChoiceValidator("store_type", Store.StoreType.choices, required=True)
            ],
            "plant": [
                ForeignKeyValidator(
                    "plant",
                    Plant,
                    lookup_field="plant_code",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "allows_negative_stock": [],  # Boolean validation handled in transform
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.

        Args:
            row_data: Raw row data from file

        Returns:
            Transformed data dictionary
        """
        field_mapping = self.get_field_mapping()
        transformed = {}

        # Create case-insensitive lookup
        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        # Map and normalize values
        for col_name, field_name in field_mapping.items():
            # Try exact match first
            if col_name in row_data:
                value = row_data[col_name]
            else:
                # Try case-insensitive match
                col_name_lower = col_name.strip().lower()
                if col_name_lower in row_data_lower:
                    original_key, value = row_data_lower[col_name_lower]
                else:
                    value = None
                    if field_name in [
                        "store_code",
                        "store_name",
                        "store_type",
                        "plant",
                    ]:
                        logger.warning(
                            f"Column '{col_name}' not found in row data. Available columns: {list(row_data.keys())}"
                        )

            if field_name == "store_code":
                # Normalize store code
                transformed[field_name] = normalize_string(value) if value else None
            elif field_name == "store_name":
                # Normalize store name
                transformed[field_name] = normalize_string(value) if value else None
            elif field_name == "store_type":
                # Normalize store type (should match StoreType choices)
                transformed[field_name] = (
                    normalize_choice(value, Store.StoreType.choices) if value else None
                )
            elif field_name == "plant":
                # Convert plant_code to Plant instance
                if value:
                    plant_code = (
                        normalize_string(value)
                        if isinstance(value, str)
                        else str(value)
                    )

                    # Check cache first
                    if plant_code in self.plant_cache:
                        transformed[field_name] = self.plant_cache[plant_code]
                    else:
                        # Look up Plant by plant_code
                        try:
                            plant = Plant.objects.filter(
                                plant_code__iexact=plant_code, deleted=False
                            ).first()

                            if plant:
                                self.plant_cache[plant_code] = plant
                                transformed[field_name] = plant
                            else:
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(
                                f"Error looking up Plant with code '{plant_code}': {str(e)}"
                            )
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name == "allows_negative_stock":
                # Handle boolean
                if value is None or value == "":
                    transformed[field_name] = False
                elif isinstance(value, bool):
                    transformed[field_name] = value
                elif isinstance(value, str):
                    value_lower = value.strip().lower()
                    transformed[field_name] = value_lower in ("true", "1", "yes", "y")
                else:
                    transformed[field_name] = bool(value)
            else:
                transformed[field_name] = value

        # Add audit fields
        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> Store:
        """
        Create Store model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            Store instance (not saved)
        """
        return Store(**validated_data)
