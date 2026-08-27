"""
Inspection Type Master bulk importer
"""

import logging
from typing import Any, Dict, List

from django.utils import timezone

from common.models import InspectionType, Plant
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    StringValidator,
    UniqueValidator,
)

logger = logging.getLogger(__name__)


class InspectionTypeImporter(BaseImporter):
    """Bulk importer for Inspection Type Master module"""

    MODULE_NAME = "InspectionType"
    REQUIRED_COLUMNS = [
        "Code",
        "Name",
        "Process Stage",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_codes = set()
        self.plant_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Code": "code",
            "Name": "name",
            "Process Stage": "process_stage",
            "Requires Sampling": "requires_sampling",
            "Requires Lab Test": "requires_lab_test",
            "Plant Code": "plant_code",
            "Description": "description",
            "Is Active": "is_active",
        }

    def get_validators(self) -> Dict[str, List]:
        return {
            "code": [
                UniqueValidator("code", self.seen_codes, required=True),
                StringValidator(
                    "code", max_length=50, required=True, pattern=r"^[A-Z0-9_-]+$"
                ),
            ],
            "name": [
                StringValidator("name", max_length=255, required=True),
            ],
            "process_stage": [
                ChoiceValidator(
                    "process_stage",
                    InspectionType.PROCESS_STAGE_CHOICES,
                    required=True,
                )
            ],
            "requires_sampling": [],
            "requires_lab_test": [],
            "plant_code": [],
            "description": [
                StringValidator("description", max_length=1000, required=False),
            ],
            "is_active": [],
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
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
                    _, value = row_data_lower[col_name_lower]
                else:
                    value = None

            if field_name == "code":
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "process_stage":
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name in ("requires_sampling", "requires_lab_test"):
                if value is None or value == "":
                    transformed[field_name] = False
                else:
                    val = str(value).strip().lower()
                    transformed[field_name] = val in ("true", "1", "yes", "y")
            elif field_name == "is_active":
                if value is None or value == "":
                    transformed[field_name] = True
                else:
                    val = str(value).strip().lower()
                    transformed[field_name] = val in ("true", "1", "yes", "y")
            elif field_name == "plant_code":
                plant_code = normalize_string(value) if value else None
                if plant_code:
                    plant_code_upper = plant_code.upper()
                    if plant_code_upper in self.plant_cache:
                        transformed["plant"] = self.plant_cache[plant_code_upper]
                    else:
                        plant = Plant.objects.filter(
                            plant_code__iexact=plant_code_upper, deleted=False
                        ).first()
                        if plant:
                            self.plant_cache[plant_code_upper] = plant
                            transformed["plant"] = plant
                        else:
                            transformed["plant"] = None
                else:
                    transformed["plant"] = None
            elif field_name == "description":
                transformed[field_name] = normalize_string(value) if value else None
            else:
                transformed[field_name] = normalize_string(value) if value else None

        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["is_archived"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> InspectionType:
        # Remove plant_code if present (we use plant FK)
        data = dict(validated_data)
        data.pop("plant_code", None)
        return InspectionType(**data)

    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
        if not hasattr(self, "row_errors"):
            self.row_errors = []
        formatted = []
        for err in errors:
            formatted.append(
                {
                    "field": err.get("field", "unknown"),
                    "message": err.get("message", "Validation failed"),
                    "value": str(err.get("value", "")) if err.get("value") else None,
                }
            )
        self.row_errors.append(
            {
                "row_number": row_number,
                "errors": formatted,
                "row_data": dict(row_data),
            }
        )

    def _save_errors_to_database(self) -> None:
        if not self.import_log or not getattr(self, "row_errors", None):
            return
        from imports.models import ImportErrorRow

        for row in self.row_errors:
            row_number = row.get("row_number")
            raw_data = (
                row.get("row_data") if isinstance(row.get("row_data"), dict) else {}
            )
            errors = row.get("errors") or []
            if not isinstance(errors, list) or not errors:
                errors = [
                    {"field": None, "message": "Validation failed", "value": None}
                ]
            for err in errors:
                try:
                    ImportErrorRow.objects.create(
                        import_log=self.import_log,
                        row_number=row_number or 0,
                        error_type="validation",
                        field_name=err.get("field") or "",
                        error_message=str(err.get("message", "")),
                        raw_data=raw_data,
                    )
                except Exception as e:
                    logger.error(f"Error creating ImportErrorRow: {e}", exc_info=True)

    def validate_all_rows(self) -> tuple[int, int]:
        if not self.parser:
            return 0, 0
        rows = self.parser.get_rows()
        if not rows:
            return 0, 0

        valid_count = 0
        error_count = 0
        header_offset = getattr(self.parser, "header_row", 0)

        for idx, row_data in enumerate(rows, start=1):
            actual_row = idx + header_offset + 1
            try:
                transformed = self.transform_row_data(row_data)
                is_valid, errors = self.validate_row(row_data, actual_row)

                if is_valid:
                    transformed["_row_number"] = actual_row
                    transformed["_original_row_data"] = dict(row_data)
                    self.validated_data.append(transformed)
                    valid_count += 1
                else:
                    error_count += 1
                    self._add_row_error(actual_row, errors, row_data)
            except Exception as e:
                error_count += 1
                logger.error(f"Row {actual_row} error: {e}", exc_info=True)
                self._add_row_error(
                    actual_row,
                    [{"field": "unknown", "message": str(e), "value": None}],
                    row_data,
                )

        return valid_count, error_count

    def save_data(self) -> tuple[int, int, int, int]:
        if not self.validated_data:
            return 0, 0, 0, 0

        inserted = 0
        failed = 0

        for data in list(self.validated_data):
            try:
                row_num = data.pop("_row_number", None)
                data.pop("_original_row_data", None)
                data.pop("plant_code", None)

                if self.dry_run:
                    inserted += 1
                    continue

                # Check for existing by code (case-insensitive)
                code = data.get("code")
                existing = InspectionType.objects.filter(
                    code__iexact=code, is_archived=False
                ).first()

                if existing:
                    for key, value in data.items():
                        if key not in ("created_by", "created_at"):
                            setattr(existing, key, value)
                    existing.updated_by = self.user
                    existing.updated_at = timezone.now()
                    existing.save()
                    inserted += 1
                else:
                    InspectionType.objects.create(**data)
                    inserted += 1
            except Exception as e:
                failed += 1
                logger.error(f"Save error: {e}", exc_info=True)

        return inserted, 0, 0, failed

    def import_data(self) -> Dict[str, Any]:
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": error,
                "total_rows": 0,
                "success_count": 0,
                "error_count": 0,
                "import_log_id": None,
            }

        self.create_import_log()

        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            return {
                "success": False,
                "message": error,
                "total_rows": 0,
                "success_count": 0,
                "error_count": 0,
                "import_log_id": str(self.import_log.id) if self.import_log else None,
            }

        total_rows = self.parser.get_row_count()
        valid_count, error_count = self.validate_all_rows()

        if not self.dry_run and getattr(self, "row_errors", None):
            self._save_errors_to_database()

        inserted = 0
        failed = 0
        if not self.dry_run and valid_count > 0:
            inserted, _, _, failed = self.save_data()

        if self.import_log:
            total_saved = inserted
            total_errors = error_count + failed
            self.import_log.mark_completed(total_saved, total_errors)

        return {
            "success": inserted > 0,
            "message": f"Import completed: {inserted} inserted, {error_count + failed} errors",
            "total_rows": total_rows,
            "success_count": inserted,
            "error_count": error_count + failed,
            "dry_run": self.dry_run,
            "import_log_id": str(self.import_log.id) if self.import_log else None,
        }
