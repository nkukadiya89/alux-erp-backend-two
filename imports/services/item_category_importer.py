"""
Item Category Master bulk importer
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from common.models import ItemCategory
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_choice, normalize_string
from imports.validators.field_validators import (
    ChoiceValidator,
    StringValidator,
    UniqueValidator,
)

logger = logging.getLogger(__name__)


class ItemCategoryImporter(BaseImporter):
    """
    Bulk importer for Item Category Master module
    """

    MODULE_NAME = "Item Category"
    REQUIRED_COLUMNS = [
        "Category Code",
        "Category Name",
        "Allowed Item Type",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_category_codes = set()

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV columns to model fields.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        return {
            "Category Code": "category_code",
            "Category Name": "category_name",
            "Allowed Item Type": "allowed_item_type",
            "Description": "description",
            "Status": "status",
            "Is Active": "status",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        return {
            "category_code": [
                UniqueValidator(
                    "category_code", self.seen_category_codes, required=True
                ),
                StringValidator(
                    "category_code",
                    max_length=50,
                    required=True,
                    pattern=r"^[A-Z0-9_-]+$",
                ),
            ],
            "category_name": [
                StringValidator("category_name", max_length=255, required=True)
            ],
            "allowed_item_type": [
                ChoiceValidator(
                    "allowed_item_type", ItemCategory.ITEM_TYPE_CHOICES, required=True
                )
            ],
            "description": [
                StringValidator("description", max_length=None, required=False)
            ],
            "status": [
                ChoiceValidator("status", ItemCategory.STATUS_CHOICES, required=False)
            ],
        }

    def _normalize_for_compare(self, field_name: str, value: Any) -> Any:
        """Normalize values for exact-duplicate comparison."""
        if value is None:
            return None
        if isinstance(value, str):
            v = value.strip()
            return v if v != "" else None
        return value

    def _is_exact_duplicate(self, existing: ItemCategory, data: Dict) -> bool:
        """
        Return True if incoming row matches the existing record exactly (ignoring audit fields),
        so we should count it as skipped (not updated).
        """
        compare_fields = [
            "category_code",
            "category_name",
            "allowed_item_type",
            "description",
            "status",
            "is_archived",
        ]
        for f in compare_fields:
            old_val = getattr(existing, f, None)
            new_val = data.get(f)
            if self._normalize_for_compare(f, old_val) != self._normalize_for_compare(
                f, new_val
            ):
                return False
        return True

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
                        "category_code",
                        "category_name",
                        "allowed_item_type",
                    ]:
                        logger.warning(
                            f"Column '{col_name}' not found in row data. Available columns: {list(row_data.keys())}"
                        )

            if field_name == "category_code":

                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "allowed_item_type":

                transformed[field_name] = normalize_choice(
                    value, ItemCategory.ITEM_TYPE_CHOICES
                )
            elif field_name == "status":
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    transformed[field_name] = "Active"
                else:
                    s = str(value).strip().lower()
                    if s in ("true", "1", "yes"):
                        transformed[field_name] = "Active"
                    elif s in ("false", "0", "no"):
                        transformed[field_name] = "Inactive"
                    else:
                        transformed[field_name] = (
                            normalize_choice(value, ItemCategory.STATUS_CHOICES)
                            or "Active"
                        )
            else:
                transformed[field_name] = normalize_string(value)

        transformed["created_by"] = self.user
        transformed["is_archived"] = False

        if "_row_number" in row_data:
            transformed["_row_number"] = row_data["_row_number"]
        transformed["_original_row_data"] = {
            k: v for k, v in row_data.items() if k not in ("_row_number",)
        }

        return transformed

    def create_model_instance(self, validated_data: Dict) -> ItemCategory:
        """
        Create ItemCategory model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            ItemCategory instance (not saved)
        """
        exclude = (
            "_row_number",
            "_original_row_data",
            "updated_at",
            "updated_by",
            "created_at",
        )
        model_data = {k: v for k, v in validated_data.items() if k not in exclude}
        return ItemCategory(**model_data)

    def save_data(self) -> tuple[int, int, int, int]:
        """
        Save validated data to database with row-level progress tracking.

        Returns:
            Tuple of (inserted_count, updated_count, skipped_count, failed_count)
        """
        if self.dry_run:
            logger.info(
                "Dry run mode - skipping data save",
                extra={
                    "module_name": self.MODULE_NAME,
                    "total_records": len(self.validated_data),
                },
            )
            return len(self.validated_data), 0, 0, 0

        if not self.validated_data:
            logger.warning(
                "No validated data to save", extra={"module_name": self.MODULE_NAME}
            )
            return 0, 0, 0, []

        total_records = len(self.validated_data)
        logger.info(
            "Starting bulk save operation",
            extra={
                "module_name": self.MODULE_NAME,
                "total_records": total_records,
                "batch_size": self.BATCH_SIZE,
            },
        )

        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0

        for batch_start in range(0, total_records, self.BATCH_SIZE):
            batch_end = min(batch_start + self.BATCH_SIZE, total_records)
            batch_data = self.validated_data[batch_start:batch_end]
            batch_number = (batch_start // self.BATCH_SIZE) + 1
            total_batches = (total_records + self.BATCH_SIZE - 1) // self.BATCH_SIZE

            logger.info(
                "Processing batch",
                extra={
                    "module_name": self.MODULE_NAME,
                    "batch_number": batch_number,
                    "total_batches": total_batches,
                    "batch_start": batch_start + 1,
                    "batch_end": batch_end,
                    "batch_size": len(batch_data),
                    "progress_percent": round((batch_end / total_records) * 100, 2),
                },
            )

            for idx, data in enumerate(batch_data):
                row_number = data.get("_row_number", batch_start + idx + 1)
                category_code = data.get("category_code", "N/A")
                category_name = data.get("category_name", "N/A")

                try:
                    existing_category = ItemCategory.objects.filter(
                        category_code__iexact=category_code, is_archived=False
                    ).first()

                    if existing_category:
                        if self._is_exact_duplicate(existing_category, data):
                            skipped_count += 1
                            logger.debug(
                                "Skipped exact-duplicate category",
                                extra={
                                    "module_name": self.MODULE_NAME,
                                    "row_number": row_number,
                                    "category_code": category_code,
                                },
                            )
                        else:
                            changed = False
                            for key, value in data.items():
                                if key in [
                                    "id",
                                    "created_at",
                                    "created_by",
                                    "_row_number",
                                    "_original_row_data",
                                ]:
                                    continue
                                old_val = getattr(existing_category, key, None)
                                if self._normalize_for_compare(
                                    key, old_val
                                ) != self._normalize_for_compare(key, value):
                                    setattr(existing_category, key, value)
                                    changed = True

                            if changed:
                                existing_category.updated_by = self.user
                                existing_category.updated_at = timezone.now()
                                existing_category.save()
                                updated_count += 1
                                logger.debug(
                                    "Updated existing category",
                                    extra={
                                        "module_name": self.MODULE_NAME,
                                        "row_number": row_number,
                                        "category_code": category_code,
                                    },
                                )
                            else:
                                skipped_count += 1
                                logger.debug(
                                    "Skipped unchanged category",
                                    extra={
                                        "module_name": self.MODULE_NAME,
                                        "row_number": row_number,
                                        "category_code": category_code,
                                    },
                                )
                    else:
                        instance = self.create_model_instance(data)
                        instance.save()
                        inserted_count += 1

                        logger.debug(
                            "Inserted new category",
                            extra={
                                "module_name": self.MODULE_NAME,
                                "row_number": row_number,
                                "category_code": category_code,
                            },
                        )

                except Exception as save_error:
                    failed_count += 1

                    logger.error(
                        "Skipped record due to error",
                        extra={
                            "module_name": self.MODULE_NAME,
                            "row_number": row_number,
                            "category_code": category_code,
                            "error": str(save_error),
                        },
                        exc_info=True,
                    )

        logger.info(
            "Bulk save operation completed",
            extra={
                "module_name": self.MODULE_NAME,
                "total_records": total_records,
                "inserted_count": inserted_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
                "success_rate": (
                    round(((inserted_count + updated_count) / total_records) * 100, 2)
                    if total_records > 0
                    else 0
                ),
            },
        )

        return inserted_count, updated_count, skipped_count, failed_count

    def _add_row_error(
        self, row_number: int, errors: List[Dict], row_data: Optional[Dict] = None
    ) -> None:
        """Add a row error to row_errors list (alloy_importer style)."""
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
        self.row_errors.append(
            {
                "row_number": row_number,
                "errors": formatted_errors,
                "row_data": row_data if isinstance(row_data, dict) else {},
            }
        )

    def _save_errors_to_database(self) -> None:
        """Persist collected row_errors to ImportErrorRow table (alloy_importer style)."""
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

    def import_data(self) -> Dict[str, Any]:
        """Run import and return result including row_errors (and persist to ImportErrorRow)."""
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": error,
                "total_rows": 0,
                "total_records": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "success_count": 0,
                "error_count": 0,
                "dry_run": self.dry_run,
                "import_log_id": "",
                "row_errors": [],
            }
        try:
            self.create_import_log()
        except Exception as e:
            logger.error(f"Error creating import log: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "total_rows": 0,
                "total_records": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "success_count": 0,
                "error_count": 0,
                "dry_run": self.dry_run,
                "import_log_id": "",
                "row_errors": [],
            }
        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            return {
                "success": False,
                "message": error,
                "total_rows": 0,
                "total_records": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "success_count": 0,
                "error_count": 0,
                "dry_run": self.dry_run,
                "import_log_id": str(self.import_log.id) if self.import_log else "",
                "row_errors": [],
            }
        total_rows = self.parser.get_row_count()
        valid_count, error_count = self.validate_all_rows()
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        if not self.dry_run and valid_count > 0:
            try:
                inserted_count, updated_count, skipped_count, failed_count = (
                    self.save_data()
                )
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}", exc_info=True)
                if self.import_log:
                    self.import_log.mark_failed(str(e))
                return {
                    "success": False,
                    "message": f"Error saving data: {str(e)}",
                    "total_rows": total_rows,
                    "total_records": valid_count,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "success_count": 0,
                    "error_count": valid_count + error_count,
                    "dry_run": self.dry_run,
                    "import_log_id": str(self.import_log.id) if self.import_log else "",
                    "row_errors": getattr(self, "row_errors", []),
                }
        if not self.dry_run and getattr(self, "row_errors", None):
            self._save_errors_to_database()
        if self.import_log:
            total_saved = inserted_count + updated_count
            total_errors = error_count + failed_count
            self.import_log.mark_completed(total_saved, total_errors)
        # Only show top 10 row_errors in response (match alloy_importer); full count in error_count
        row_errors_all = getattr(self, "row_errors", []) or []
        row_errors = row_errors_all[:10]
        skipped_total = skipped_count + error_count
        errors_total = error_count + failed_count
        return {
            "success": bool(
                inserted_count > 0 or updated_count > 0 or skipped_count > 0
            ),
            "message": (
                f"Import completed: {inserted_count} inserted, {updated_count} updated, "
                f"{skipped_total} skipped, {errors_total} errors"
            ),
            "total_rows": total_rows,
            "total_records": valid_count,
            "inserted": inserted_count,
            "updated": updated_count,
            "skipped": skipped_total,
            "success_count": inserted_count + updated_count,
            "error_count": errors_total,
            "dry_run": self.dry_run,
            "import_log_id": str(self.import_log.id) if self.import_log else "",
            "row_errors": row_errors,
        }
