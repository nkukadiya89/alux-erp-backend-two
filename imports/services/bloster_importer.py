"""
BlosterMaster bulk importer
"""

import logging
from typing import Dict, List

from django.utils import timezone

from bloster.models import BlosterMaster
from die.models import DiePress
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string
from imports.validators.field_validators import StringValidator, UniqueValidator
from imports.validators.reference_validators import ForeignKeyValidator

logger = logging.getLogger(__name__)


class BlosterImporter(BaseImporter):
    """
    Bulk importer for BlosterMaster module
    """

    MODULE_NAME = "BlosterMaster"
    REQUIRED_COLUMNS = [
        "Bloster No",
        "Press Name",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_bloster_nos = set()
        self.press_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Bloster No": "bloster_no",
            "Press Name": "press",
            "Size": "size",
            "Type": "type",
            "Description": "description",
            "Bloster Image": "bloster_image",
            "Autocard": "autocard",
            "PDF": "pdf",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "bloster_no": [
                UniqueValidator("bloster_no", self.seen_bloster_nos, required=True),
                StringValidator("bloster_no", max_length=100, required=True),
            ],
            "press": [
                ForeignKeyValidator(
                    "press",
                    DiePress,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "size": [
                StringValidator("size", required=False),
            ],
            "type": [
                StringValidator("type", max_length=100, required=False),
            ],
            "description": [
                StringValidator("description", required=False),
            ],
            "bloster_image": [
                StringValidator("bloster_image", max_length=250, required=False),
            ],
            "autocard": [
                StringValidator("autocard", max_length=250, required=False),
            ],
            "pdf": [
                StringValidator("pdf", max_length=250, required=False),
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

        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        for col_name, field_name in field_mapping.items():
            if col_name in row_data:
                value = row_data[col_name]
            else:
                col_name_lower = col_name.strip().lower()
                if col_name_lower in row_data_lower:
                    original_key, value = row_data_lower[col_name_lower]
                else:
                    value = None
                    if field_name in ["bloster_no", "press"]:
                        logger.warning(
                            f"Column '{col_name}' not found in row data. Available columns: {list(row_data.keys())}"
                        )

            if field_name == "bloster_no":
                transformed[field_name] = normalize_string(value) if value else None
            elif field_name == "press":
                if value:
                    press_name = (
                        normalize_string(value)
                        if isinstance(value, str)
                        else str(value)
                    )

                    if press_name in self.press_cache:
                        transformed[field_name] = self.press_cache[press_name]
                    else:
                        try:
                            press = DiePress.objects.filter(
                                name__iexact=press_name, deleted=False
                            ).first()

                            if press:
                                self.press_cache[press_name] = press
                                transformed[field_name] = press
                            else:
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(
                                f"Error looking up DiePress with name '{press_name}': {str(e)}"
                            )
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name == "size":
                try:
                    transformed[field_name] = int(value) if value else None
                except (ValueError, TypeError):
                    transformed[field_name] = None
            else:
                transformed[field_name] = normalize_string(value) if value else None

        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> BlosterMaster:
        """
        Create BlosterMaster model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            BlosterMaster instance (not saved)
        """
        return BlosterMaster(**validated_data)
