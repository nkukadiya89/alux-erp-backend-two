"""
DieCategory Master bulk importer
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from imports.services.base_importer import BaseImporter
from imports.validators.field_validators import StringValidator
from imports.validators.reference_validators import DatabaseUniqueValidator


class DieCategoryUniqueValidator(DatabaseUniqueValidator):
    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        try:
            lookup_kwargs = (
                {f"{self.lookup_field}__iexact": value.strip()}
                if isinstance(value, str)
                else {self.lookup_field: value}
            )
            queryset = self.model_class.objects.filter(**lookup_kwargs, deleted=False)

            if self.exclude_id:
                queryset = queryset.exclude(pk=self.exclude_id)

            if queryset.exists():
                return False, f"{self.field_name} '{value}' already exists in database"

            return True, None
        except Exception as e:
            logger.error(f"Error validating uniqueness for {self.field_name}: {str(e)}")
            return False, f"Error validating {self.field_name}: {str(e)}"


from die.models import DieCategory
from imports.utils import normalize_string

logger = logging.getLogger(__name__)


class DieCategoryImporter(BaseImporter):
    """
    Bulk importer for DieCategory Master module
    """

    MODULE_NAME = "DieCategory"
    REQUIRED_COLUMNS = [
        "Name",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_names = set()

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Name": "name",
            "Description": "description",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "name": [
                StringValidator("name", max_length=50, required=True),
            ],
            "description": [
                StringValidator("description", max_length=500, required=False),
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
                    if field_name in ["name"]:
                        logger.warning(
                            f"Column '{col_name}' not found in row data. Available columns: {list(row_data.keys())}"
                        )

            if field_name in ["name", "description"]:
                transformed[field_name] = normalize_string(value) if value else None
            else:
                transformed[field_name] = normalize_string(value) if value else None

        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> DieCategory:
        """
        Create DieCategory model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            DieCategory instance (not saved)
        """
        return DieCategory(**validated_data)

    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
        """Helper to add row error to row_errors list with proper formatting"""
        if not hasattr(self, "row_errors"):
            self.row_errors = []

        formatted_errors = []
        for error in errors:
            formatted_errors.append(
                {
                    "field": error.get("field", "unknown"),
                    "message": error.get("message", "Validation failed"),
                    "value": (
                        str(error.get("value", ""))
                        if error.get("value") is not None
                        else None
                    ),
                }
            )

        self.row_errors.append({"row_number": row_number, "errors": formatted_errors})

    def _save_errors_to_database(self) -> None:
        """Persist collected row errors to ImportErrorRow table"""
        if not self.import_log or not getattr(self, "row_errors", None):
            return

        try:
            from imports.models import ImportErrorRow
        except Exception as e:
            logger.error(f"Unable to import ImportErrorRow: {str(e)}", exc_info=True)
            return

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
                    field_name = err.get("field") if isinstance(err, dict) else None
                    error_message = (
                        err.get("message") if isinstance(err, dict) else str(err)
                    )
                    ImportErrorRow.objects.create(
                        import_log=self.import_log,
                        row_number=row_number or 0,
                        error_type="validation",
                        field_name=field_name or "",
                        error_message=str(error_message),
                        raw_data=raw_data,
                    )
                except Exception as e:
                    logger.error(
                        f"Error creating ImportErrorRow for row {row_number}: {str(e)}",
                        exc_info=True,
                    )

    def validate_all_rows(self) -> tuple[int, int]:
        """
        Override to track row errors properly.
        Row numbers start at 2 (header is row 1)
        """
        if not self.parser:
            return 0, 0

        rows = self.parser.get_rows()
        if not rows:
            return 0, 0

        valid_count = 0
        error_count = 0

        for idx, row_data in enumerate(rows, start=2):
            try:
                try:
                    transformed = self.transform_row_data(row_data)
                except Exception as e:
                    logger.error(
                        f"Error transforming row {idx}: {str(e)}", exc_info=True
                    )
                    error_count += 1
                    self._add_row_error(
                        idx,
                        [
                            {
                                "field": "transformation",
                                "message": f"Row {idx}: Error transforming data: {str(e)}",
                                "value": None,
                            }
                        ],
                        row_data,
                    )
                    continue

                is_valid, errors = self.validate_row(row_data, idx)

                if is_valid:
                    transformed["_row_number"] = idx
                    transformed["_original_row_data"] = dict(row_data)
                    self.validated_data.append(transformed)
                    valid_count += 1
                else:
                    error_count += 1
                    self._add_row_error(idx, errors, row_data)

            except Exception as e:
                error_count += 1
                logger.error(f"Error validating row {idx}: {str(e)}", exc_info=True)
                self._add_row_error(
                    idx,
                    [
                        {
                            "field": "unknown",
                            "message": f"Row {idx}: {str(e)}",
                            "value": None,
                        }
                    ],
                    row_data,
                )

        return valid_count, error_count

    def save_data(self) -> tuple[int, int, int, int, List[Dict]]:
        """
        Save validated DieCategory rows.
        - Exact duplicate: Skip (do NOT add to row_errors)
        - Different data: Update
        - New record: Insert

        Returns:
            Tuple of (inserted, updated, skipped, failed, inserted_rows)
        """
        if not self.validated_data:
            return 0, 0, 0, 0, []

        inserted = 0
        updated = 0
        skipped = 0
        failed = 0
        inserted_rows = []

        for data in self.validated_data:
            try:
                row_num = data.pop("_row_number", None)
                original_row_data = data.pop("_original_row_data", {})

                name = data.get("name")
                if not name:
                    failed += 1
                    self._add_row_error(
                        row_num or 0,
                        [
                            {
                                "field": "name",
                                "message": "Name is required",
                                "value": None,
                            }
                        ],
                        original_row_data,
                    )
                    continue

                existing_records = DieCategory.objects.filter(name=name, deleted=False)

                if existing_records.exists():
                    exact_duplicate_found = False

                    for existing in existing_records:
                        is_exact_match = True
                        for key, value in data.items():
                            if key in [
                                "created_by",
                                "updated_by",
                                "created_at",
                                "updated_at",
                                "deleted",
                            ]:
                                continue
                            existing_value = getattr(existing, key, None)
                            if existing_value != value:
                                is_exact_match = False
                                break

                        if is_exact_match:
                            exact_duplicate_found = True
                            skipped += 1
                            break

                    if exact_duplicate_found:
                        continue
                    else:

                        existing_to_update = existing_records.first()

                        changed = False
                        for key, value in data.items():
                            if key in [
                                "created_by",
                                "updated_by",
                                "created_at",
                                "updated_at",
                                "deleted",
                            ]:
                                continue
                            if getattr(existing_to_update, key, None) != value:
                                setattr(existing_to_update, key, value)
                                changed = True

                        if changed:
                            if not self.dry_run:
                                existing_to_update.updated_by = self.user
                                existing_to_update.save()
                            updated += 1
                        else:
                            skipped += 1
                else:
                    if not self.dry_run:
                        DieCategory.objects.create(
                            **{
                                k: v
                                for k, v in data.items()
                                if k
                                not in [
                                    "created_by",
                                    "updated_by",
                                    "created_at",
                                    "updated_at",
                                    "deleted",
                                ]
                            },
                            created_by=self.user,
                            updated_by=self.user,
                        )
                    inserted += 1
                    if row_num:
                        inserted_rows.append({"row_number": row_num})

            except Exception as e:
                failed += 1
                row_num = data.get("_row_number", 0)
                original_row_data = data.get("_original_row_data", {})
                logger.error(f"Error saving row {row_num}: {str(e)}", exc_info=True)
                self._add_row_error(
                    row_num,
                    [
                        {
                            "field": "unknown",
                            "message": f"Error saving record: {str(e)}",
                            "value": None,
                        }
                    ],
                    original_row_data,
                )

        logger.info(
            f"Save summary: {inserted} inserted, {updated} updated, {skipped} skipped, {failed} failed"
        )
        return inserted, updated, skipped, failed, inserted_rows

    def import_data(self) -> Dict[str, Any]:
        """Main import method - bulk_import logic + CustomerType-style response (data.row_errors)"""
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": "Excel or csv file not uploaded for this particular model.",
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "import_log_id": "",
                    "row_errors": [],
                },
            }

        try:
            self.create_import_log()
            logger.info(
                f"Import log created: ID={self.import_log.id if self.import_log else 'None'}"
            )
        except Exception as e:
            logger.error(f"Error creating import log: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error initializing import: {str(e)}",
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "import_log_id": "",
                    "row_errors": [],
                },
            }

        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            error_message = (
                error
                if error
                else f"CSV/EXCEL is not valid for {self.MODULE_NAME} model"
            )
            return {
                "success": False,
                "message": error_message,
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "import_log_id": (
                        str(self.import_log.id)
                        if (self.import_log and self.import_log.id)
                        else ""
                    ),
                    "row_errors": [],
                },
            }

        total_rows = self.parser.get_row_count() if self.parser else 0

        valid_count, error_count = self.validate_all_rows()
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")

        if not self.dry_run and hasattr(self, "row_errors") and self.row_errors:
            self._save_errors_to_database()

        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        inserted_rows = []

        if not self.dry_run and valid_count > 0:
            try:
                result = self.save_data()
                if len(result) == 5:
                    (
                        inserted_count,
                        updated_count,
                        skipped_count,
                        failed_count,
                        inserted_rows,
                    ) = result
                else:
                    inserted_count, updated_count, skipped_count, failed_count = result[
                        :4
                    ]
                    inserted_rows = []
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}", exc_info=True)
                if self.import_log:
                    self.import_log.mark_failed(str(e))
                return {
                    "success": False,
                    "message": f"Error saving data: {str(e)}",
                    "data": {
                        "total_records": total_rows,
                        "inserted": 0,
                        "updated": 0,
                        "skipped": valid_count + error_count,
                        "failed": valid_count + error_count,
                        "success_count": 0,
                        "error_count": valid_count + error_count,
                        "import_log_id": (
                            str(self.import_log.id)
                            if (self.import_log and self.import_log.id)
                            else ""
                        ),
                        "row_errors": getattr(self, "row_errors", []),
                    },
                }

        failed_count += error_count

        if self.import_log:
            total_saved = inserted_count + updated_count
            total_errors = failed_count
            self.import_log.mark_completed(total_saved, total_errors)
            self.import_log.refresh_from_db()

        message_parts = []
        if inserted_count > 0:
            message_parts.append(f"{inserted_count} records inserted successfully")
        if updated_count > 0:
            message_parts.append(f"{updated_count} records updated successfully")
        if skipped_count > 0:
            message_parts.append(f"{skipped_count} record skipped successfully")
        if failed_count > 0:
            message_parts.append(f"{failed_count} records failed")

        row_errors_all = getattr(self, "row_errors", []) or []
        row_errors = row_errors_all[:10]

        return {
            "success": bool(
                inserted_count > 0 or updated_count > 0 or skipped_count > 0
            ),
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
            "data": {
                "total_records": total_rows,
                "inserted": inserted_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "success_count": inserted_count + updated_count,
                "error_count": failed_count,
                "import_log_id": (
                    str(self.import_log.id)
                    if (self.import_log and self.import_log.id)
                    else ""
                ),
                "row_errors": row_errors,
            },
        }
