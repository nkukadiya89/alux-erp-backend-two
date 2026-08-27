"""
PackingMode Master bulk importer
"""

import logging
from typing import Any, Dict, List

from django.db import IntegrityError
from django.utils import timezone

from common.models import PackingMode
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string
from imports.validators.field_validators import StringValidator, UniqueValidator

logger = logging.getLogger(__name__)


class PackingModeImporter(BaseImporter):
    """
    Bulk importer for PackingMode Master module
    """

    MODULE_NAME = "PackingMode"
    REQUIRED_COLUMNS = [
        "Name",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_names = set()  # Track names for uniqueness

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Code": "code",
            "Name": "name",
            "Description": "description",
            "Price Per Kg": "price_per_kg",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "code": [
                StringValidator("code", max_length=100, required=False),
            ],
            "name": [
                UniqueValidator("name", self.seen_names, required=True),
                StringValidator("name", max_length=100, required=True),
            ],
            "description": [
                StringValidator("description", required=False),
            ],
            "price_per_kg": [
                StringValidator("price_per_kg", required=False),
            ],
        }

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.
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

            if field_name in ["code", "name", "description", "price_per_kg"]:
                transformed[field_name] = normalize_string(value) if value else None
            else:
                transformed[field_name] = normalize_string(value) if value else None

        # Add audit fields
        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> PackingMode:
        """
        Create PackingMode model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            PackingMode instance (not saved)
        """
        # Check for existing record with same name (case-insensitive)
        name = validated_data.get("name")
        if name:
            existing = PackingMode.objects.filter(
                name__iexact=name, deleted=False
            ).first()
            if existing:
                # Update existing record instead of creating new one
                for key, value in validated_data.items():
                    if key not in [
                        "created_by",
                        "created_at",
                    ]:  # Don't overwrite created_by and created_at
                        setattr(existing, key, value)
                existing.updated_by = self.user
                existing.updated_at = timezone.now()
                return existing

        return PackingMode(**validated_data)

    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
        """Helper to add row error to row_errors list with proper formatting"""
        if not hasattr(self, "row_errors"):
            self.row_errors = []

        # Format errors to match expected structure
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

        self.row_errors.append(
            {
                "row_number": row_number,
                "errors": formatted_errors,
                "row_data": dict(row_data),
            }
        )

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

        # Row numbers start at 2 (header is row 1)
        for idx, row_data in enumerate(rows, start=2):
            try:
                # Transform data first
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
                    # Store validated data
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
        Save validated PackingMode rows.
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
                # Remove metadata fields before saving
                row_num = data.pop("_row_number", None)
                original_row_data = data.pop("_original_row_data", {})

                # Get the name from data
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

                # Check for existing records with the same name (case-insensitive)
                existing_records = PackingMode.objects.filter(
                    name__iexact=name, deleted=False
                )

                if existing_records.exists():
                    # Check if any existing record is an exact match
                    exact_duplicate_found = False

                    for existing in existing_records:
                        # Check if all non-metadata fields match exactly
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
                            # Exact duplicate found - skip silently
                            exact_duplicate_found = True
                            skipped += 1
                            break

                    if exact_duplicate_found:
                        # Already counted as skipped above
                        continue
                    else:
                        # No exact match found, but record with same name exists
                        # Update the first existing record
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
                                existing_to_update.updated_at = timezone.now()
                                existing_to_update.save()
                            updated += 1
                        else:
                            # This shouldn't happen since we already checked for exact match
                            skipped += 1
                else:
                    # No record with this name exists - create new record
                    if not self.dry_run:
                        PackingMode.objects.create(
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

            except IntegrityError:
                skipped += 1
                continue

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
        # Step 1: Validate file
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

        # Step 2: Create import log
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

        # Step 3: Parse file
        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            # Ensure error message is clear and user-friendly
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

        # Step 4: Validate rows
        valid_count, error_count = self.validate_all_rows()
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")

        # Step 5: Save errors to database
        if not self.dry_run and hasattr(self, "row_errors") and self.row_errors:
            self._save_errors_to_database()

        # Step 6: Save data
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
                    # Fallback for old format
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

        # Validation errors contribute to "failed"
        failed_count += error_count

        # Step 7: Update import log
        if self.import_log:
            total_saved = inserted_count + updated_count
            total_errors = failed_count
            self.import_log.mark_completed(total_saved, total_errors)
            self.import_log.refresh_from_db()

        # Step 8: Format response
        message_parts = []
        if inserted_count > 0:
            message_parts.append(f"{inserted_count} records inserted successfully")
        if updated_count > 0:
            message_parts.append(f"{updated_count} records updated successfully")
        if skipped_count > 0:
            message_parts.append(f"{skipped_count} record skipped successfully")
        if failed_count > 0:
            message_parts.append(f"{failed_count} records failed")

        # Only show top 10 row errors in response; keep full count in error_count
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
                # total number of errors (not limited to top 10)
                "error_count": failed_count,
                "import_log_id": (
                    str(self.import_log.id)
                    if (self.import_log and self.import_log.id)
                    else ""
                ),
                "row_errors": row_errors,
            },
        }
