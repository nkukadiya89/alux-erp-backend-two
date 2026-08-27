"""
Gate Pass bulk importer using the generic BaseImporter.
"""

import logging
from typing import Dict, List

from django.utils import timezone

from gate_pass.models import GatePass
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_choice, normalize_string
from imports.validators.field_validators import ChoiceValidator, StringValidator
from imports.validators.base import BaseValidator
from datetime import datetime

logger = logging.getLogger(__name__)


class GatePassImporter(BaseImporter):
    """
    Bulk importer for Gate Pass module.
    """

    MODULE_NAME = "GatePass"
    REQUIRED_COLUMNS = [
        "Gate Pass No",
        "Date",
        "Type",
        "Party Name",
        "Vehicle No",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    class _SimpleDateValidator(BaseValidator):
        """
        Local date validator (YYYY-MM-DD) to avoid adding global dependency.
        """

        def validate(self, value, row_data=None):
            is_valid, error = self.validate_required(value)
            if not is_valid:
                return False, error

            if not self.required and (value is None or str(value).strip() == ""):
                return True, None

            try:
                datetime.strptime(str(value).strip(), "%Y-%m-%d")
                return True, None
            except Exception:
                return False, f"{self.field_name} must be in YYYY-MM-DD format"

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.
        """
        return {
            "Gate Pass No": "gate_pass_no",
            "Date": "date",
            "Type": "type",
            "Party Name": "party_name",
            "Vehicle No": "vehicle_no",
            "Remarks": "remarks",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.
        """
        return {
            "gate_pass_no": [
                StringValidator(
                    "gate_pass_no",
                    max_length=50,
                    required=True,
                )
            ],
            "date": [
                self._SimpleDateValidator("date", required=True),
            ],
            "type": [
                ChoiceValidator(
                    "type",
                    GatePass.TYPE_CHOICES,
                    required=True,
                )
            ],
            "party_name": [
                StringValidator("party_name", max_length=255, required=True),
            ],
            "vehicle_no": [
                StringValidator("vehicle_no", max_length=50, required=True),
            ],
            "remarks": [
                StringValidator("remarks", max_length=500, required=False),
            ],
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.
        """
        field_mapping = self.get_field_mapping()
        transformed: Dict[str, object] = {}

        row_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        for col_name, field_name in field_mapping.items():
            if col_name in row_data:
                value = row_data[col_name]
            else:
                key_lower = col_name.strip().lower()
                if key_lower in row_lower:
                    _orig, value = row_lower[key_lower]
                else:
                    value = None

            if field_name == "type":
                transformed[field_name] = normalize_choice(value, GatePass.TYPE_CHOICES)
            else:
                transformed[field_name] = normalize_string(value)

        transformed["status"] = GatePass.STATUS_DRAFT
        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["is_archived"] = False
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> GatePass:
        """
        Create GatePass model instance from validated data.
        """
        return GatePass(**validated_data)
