# bulk_import/services/base_importer.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.apps import apps
from django.db import transaction

from ..models import ImportErrorRow, ImportLog
from ..parsers.csv_parser import CSVParser
from ..parsers.excel_parser import ExcelParser
from ..validators.validation_error import ValidationError
from ..writers.bulk_writer import BulkWriter


class BaseImporter(ABC):
    """Base class for all model importers"""

    parser_class = None
    validators = []
    model = None
    unique_field = None

    def __init__(self, import_job_id: int):
        self.import_job_id = import_job_id
        if self.model:
            self.model_class = (
                apps.get_model(self.model)
                if isinstance(self.model, str)
                else self.model
            )

    def process(self, file_path: str, user) -> Dict[str, Any]:
        """Main processing method"""
        try:
            parser = self._get_parser(file_path)
            rows = parser.parse()

            if not rows:
                return {"total": 0, "success": 0, "failed": 0, "errors": []}

            validated_rows = []
            errors = []

            for idx, row in enumerate(rows, start=2):
                try:
                    normalized = self.normalize(row)
                    self.validate(normalized)
                    validated_rows.append(normalized)

                except ValidationError as e:
                    errors.append(self.format_error(idx, row, e))
                except Exception as e:
                    errors.append(self.format_error(idx, row, ValidationError(str(e))))

            success_count = self.bulk_write(validated_rows)

            self.create_log(user, len(rows), success_count, errors)

            return {
                "total": len(rows),
                "success": success_count,
                "failed": len(errors),
                "errors": errors[:100],
            }

        except Exception as e:
            self.create_log(user, 0, 0, [{"error": str(e), "row": 0}])
            raise

    def _get_parser(self, file_path: str):
        """Get appropriate parser based on file extension"""
        if file_path.endswith((".xlsx", ".xls")):
            return ExcelParser(file_path)
        elif file_path.endswith(".csv"):
            return CSVParser(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    @abstractmethod
    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize row data - to be implemented by specific importers"""
        pass

    def validate(self, row: Dict[str, Any]):
        """Run all validators on the row"""
        for validator in self.validators:
            validator.validate(row)

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        """Default row validation - can be overridden by specific importers"""
        if hasattr(self, "unique_field") and self.unique_field:
            unique_value = data.get(self.unique_field)
            if not unique_value or str(unique_value).strip() == "":
                return (
                    False,
                    f"Row {row_num}: {self.unique_field.replace('_', ' ').title()} is required",
                )

        if hasattr(self, "required_fields") and self.required_fields:
            for field in self.required_fields:
                field_value = data.get(field)
                if not field_value or str(field_value).strip() == "":
                    return (
                        False,
                        f"Row {row_num}: {field.replace('_', ' ').title()} is required",
                    )

        return True, None

    def bulk_write(self, validated_rows: List[Dict[str, Any]]) -> int:
        """Bulk write validated rows to database"""
        if not validated_rows:
            return 0

        writer = BulkWriter()
        return writer.write(self.model_class, validated_rows)

    def format_error(
        self, row_number: int, row_data: Dict[str, Any], error: ValidationError
    ) -> Dict[str, Any]:
        """Format error for reporting"""
        return {
            "row_number": row_number,
            "row_data": row_data,
            "error": str(error),
            "field_errors": getattr(error, "field_errors", {}),
        }

    def create_log(self, user, total: int, success: int, errors: List[Dict]):
        """Create import log and error records"""
        import_log = ImportLog.objects.create(
            user=user,
            master=self.model._meta.label if self.model else "Unknown",
            total=total,
            success=success,
            failed=len(errors),
            file_name=f"import_{self.import_job_id}",
        )

        error_records = []
        for error in errors:
            error_records.append(
                ImportErrorRow(
                    log=import_log,
                    row_number=error.get("row_number", 0),
                    error=error.get("error", ""),
                    row_data=error.get("row_data", {}),
                )
            )

        if error_records:
            ImportErrorRow.objects.bulk_create(error_records, batch_size=100)

        return import_log
