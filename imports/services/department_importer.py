"""
Department Master bulk importer
Example implementation of BaseImporter
"""

import logging
from typing import Dict, List

from django.utils import timezone

from common.models import Department, Plant
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_choice, normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import ForeignKeyValidator

logger = logging.getLogger(__name__)


class DepartmentImporter(BaseImporter):
    """
    Bulk importer for Department Master module
    """

    MODULE_NAME = "Department"
    REQUIRED_COLUMNS = [
        "Department Code",
        "Department Name",
        "Department Type",
        "Plant Name",
        "Status",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_department_codes = set()
        self.plant_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Department Code": "department_code",
            "Department Name": "department_name",
            "Department Type": "department_type",
            "Plant Name": "plant",
            "Cost Center Code": "cost_center_code",
            "Parent Department Code": "parent_department_code",
            "Status": "status",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "department_code": [
                UniqueValidator(
                    "department_code", self.seen_department_codes, required=True
                ),
                StringValidator(
                    "department_code",
                    max_length=50,
                    required=True,
                    pattern=r"^[A-Z0-9_-]+$",
                ),
            ],
            "department_name": [
                StringValidator("department_name", max_length=255, required=True)
            ],
            "department_type": [
                ChoiceValidator(
                    "department_type", Department.DEPARTMENT_TYPE_CHOICES, required=True
                )
            ],
            "plant": [
                ForeignKeyValidator(
                    "plant",
                    Plant,
                    lookup_field="plant_name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "cost_center_code": [
                StringValidator("cost_center_code", max_length=50, required=False)
            ],
            "parent_department_code": [
                StringValidator("parent_department_code", max_length=50, required=False)
            ],
            "status": [
                ChoiceValidator("status", Department.STATUS_CHOICES, required=True)
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
                    if field_name in [
                        "department_code",
                        "department_name",
                        "department_type",
                        "plant",
                        "status",
                    ]:
                        if field_name == "plant":
                            logger.error(
                                f"Required column 'Plant Name' not found in row data. Available columns: {list(row_data.keys())}"
                            )
                        else:
                            logger.warning(
                                f"Column '{col_name}' not found in row data. Available columns: {list(row_data.keys())}"
                            )

            if field_name == "department_code":
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "plant":
                if value:
                    plant_name = (
                        normalize_string(value)
                        if isinstance(value, str)
                        else str(value)
                    )

                    plant_name_lower = plant_name.lower() if plant_name else ""
                    if plant_name_lower in self.plant_cache:
                        transformed[field_name] = self.plant_cache[plant_name_lower]
                    else:
                        try:
                            plant = Plant.objects.filter(
                                plant_name__iexact=plant_name, deleted=False
                            ).first()

                            if plant:
                                self.plant_cache[plant_name_lower] = plant
                                transformed[field_name] = plant
                            else:
                                logger.warning(
                                    f"Plant with name '{plant_name}' not found"
                                )
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(
                                f"Error looking up Plant '{plant_name}': {str(e)}"
                            )
                            transformed[field_name] = None
                else:
                    logger.warning("Plant Name is required but not provided")
                    transformed[field_name] = None
            elif field_name == "parent_department_code":
                if value:
                    transformed["_parent_department_code"] = (
                        normalize_string(value).upper()
                        if isinstance(value, str)
                        else str(value).upper()
                    )
            elif field_name == "status":
                transformed[field_name] = normalize_choice(
                    value, Department.STATUS_CHOICES
                )
            elif field_name == "department_type":
                transformed[field_name] = normalize_choice(
                    value, Department.DEPARTMENT_TYPE_CHOICES
                )
            else:
                transformed[field_name] = normalize_string(value)

        if "_parent_department_code" in transformed:
            parent_code = transformed.pop("_parent_department_code")
            plant = transformed.get("plant")
            try:
                if plant:
                    parent_dept = Department.objects.filter(
                        department_code__iexact=parent_code,
                        plant=plant,
                        is_archived=False,
                    ).first()

                    transformed["parent_department"] = (
                        parent_dept if parent_dept else None
                    )
                    if parent_code and not parent_dept:
                        logger.warning(
                            f"Parent department with code '{parent_code}' not found in plant '{plant.plant_name}'"
                        )
                else:
                    logger.error(
                        f"Plant is required but not set. Cannot lookup parent department '{parent_code}'"
                    )
                    transformed["parent_department"] = None
            except Exception as e:
                logger.error(
                    f"Error looking up parent department '{parent_code}': {str(e)}"
                )
                transformed["parent_department"] = None

        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["is_archived"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> Department:
        """
        Create Department model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            Department instance (not saved)
        """
        return Department(**validated_data)
