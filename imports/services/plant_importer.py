"""
Plant Master bulk importer
Example implementation of BaseImporter
"""

import logging
import uuid
from typing import Dict, List

from django.utils import timezone

from common.models import Plant, PlantType
from imports.services.base_importer import BaseImporter
from imports.utils import (
    normalize_choice,
    normalize_email,
    normalize_phone,
    normalize_string,
)
from imports.validators.base import CompositeValidator
from imports.validators.field_validators import (
    ChoiceValidator,
    EmailValidator,
    PhoneValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import (
    DatabaseUniqueValidator,
    ForeignKeyValidator,
)

logger = logging.getLogger(__name__)


class PlantImporter(BaseImporter):
    """
    Bulk importer for Plant Master module
    """

    MODULE_NAME = "Plant"
    REQUIRED_COLUMNS = [
        "Plant Code",
        "Plant Name",
        "Plant Type",
        "Address Line 1",
        "City",
        "State",
        "Country",
        "Postal Code",
        "Phone Number",
        "Email",
        "Plant Head Name",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_plant_codes = set()  # Track plant codes for uniqueness
        self.plant_type_cache = {}  # Cache PlantType lookups by code

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Plant Code": "plant_code",
            "Plant Name": "plant_name",
            "Plant Type": "plant_type",
            "Status": "status",
            "Address Line 1": "address_line_1",
            "Address Line 2": "address_line_2",
            "City": "city",
            "State": "state",
            "Country": "country",
            "Postal Code": "postal_code",
            "Phone Number": "phone_number",
            "Email": "email",
            "Plant Head Name": "plant_head_name",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        # Plant code validators
        # Note: DatabaseUniqueValidator checks if code already exists in DB
        # For bulk import, we typically want to skip existing records or update them
        # For now, we'll allow duplicates in DB (they'll fail at DB level if unique constraint exists)
        plant_code_validators = [
            UniqueValidator("plant_code", self.seen_plant_codes, required=True),
            StringValidator(
                "plant_code", max_length=50, required=True, pattern=r"^[A-Z0-9_-]+$"
            ),
            # Commented out DatabaseUniqueValidator to allow importing even if plants exist
            # Uncomment if you want to prevent importing existing plant codes
            # DatabaseUniqueValidator(
            #     "plant_code",
            #     Plant,
            #     lookup_field="plant_code",
            #     required=True,
            #     case_sensitive=False
            # )
        ]

        return {
            "plant_code": plant_code_validators,
            "plant_name": [
                StringValidator("plant_name", max_length=255, required=True)
            ],
            "plant_type": [
                ForeignKeyValidator(
                    "plant_type",
                    PlantType,
                    lookup_field="code",
                    required=True,
                    case_sensitive=False,  # Case-insensitive lookup (code is stored as uppercase)
                )
            ],
            "status": [ChoiceValidator("status", Plant.STATUS_CHOICES, required=True)],
            "address_line_1": [
                StringValidator("address_line_1", max_length=255, required=True)
            ],
            "address_line_2": [
                StringValidator("address_line_2", max_length=255, required=False)
            ],
            "city": [StringValidator("city", max_length=100, required=True)],
            "state": [StringValidator("state", max_length=100, required=True)],
            "country": [StringValidator("country", max_length=100, required=True)],
            "postal_code": [
                StringValidator("postal_code", max_length=20, required=True)
            ],
            "phone_number": [
                PhoneValidator(
                    "phone_number", min_length=10, max_length=20, required=True
                )
            ],
            "email": [EmailValidator("email", required=True)],
            "plant_head_name": [
                StringValidator("plant_head_name", max_length=255, required=True)
            ],
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
                    logger.warning(
                        f"Column '{col_name}' not found in row data. Available columns: {list(row_data.keys())}"
                    )

            if field_name == "plant_code":
                # Normalize to uppercase
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "email":
                transformed[field_name] = normalize_email(value)
            elif field_name == "phone_number":
                transformed[field_name] = normalize_phone(value)
            elif field_name == "plant_type":
                # Convert plant_type code to PlantType instance
                if value:
                    # Normalize to uppercase (PlantType codes are uppercase)
                    plant_type_code = (
                        normalize_string(value).upper()
                        if isinstance(value, str)
                        else str(value).upper()
                    )

                    # Check cache first
                    if plant_type_code in self.plant_type_cache:
                        transformed[field_name] = self.plant_type_cache[plant_type_code]
                    else:
                        # Look up PlantType by code
                        try:
                            plant_type = PlantType.objects.filter(
                                code__iexact=plant_type_code, is_deleted=False
                            ).first()

                            if plant_type:
                                self.plant_type_cache[plant_type_code] = plant_type
                                transformed[field_name] = plant_type
                            else:
                                # If not found, set to None (validation will catch this)
                                logger.warning(
                                    f"PlantType with code '{plant_type_code}' not found"
                                )
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(
                                f"Error looking up PlantType '{plant_type_code}': {str(e)}"
                            )
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name == "status":
                # Normalize status choice field
                transformed[field_name] = normalize_choice(value, Plant.STATUS_CHOICES)
            else:
                transformed[field_name] = normalize_string(value)

        # Add audit fields
        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> Plant:
        """
        Create Plant model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            Plant instance (not saved)
        """
        return Plant(**validated_data)
