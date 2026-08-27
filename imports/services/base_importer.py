"""
Base importer class for generic bulk import functionality
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from imports.models import ImportLog
from imports.parsers.csv_parser import CSVParser
from imports.parsers.excel_parser import ExcelParser

# from imports.reports.error_report import ErrorReport
from imports.utils import get_file_type, validate_file_extension
from imports.writers.bulk_writer import BulkWriter

logger = logging.getLogger(__name__)


class BaseImporter(ABC):
    """
    Abstract base class for all importers.
    Provides common functionality for parsing, validation, and bulk writing.
    """

    # Override these in subclasses
    MODULE_NAME = "Generic"  # e.g., "Plant", "Customer"
    REQUIRED_COLUMNS = []  # List of required column names
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 1000  # Batch size for bulk operations

    def __init__(self, file, user=None, dry_run: bool = False):
        """
        Initialize importer.

        Args:
            file: File object to import
            user: User performing the import
            dry_run: If True, validate only without saving
        """
        self.file = file
        # Reset file pointer to beginning in case it was read before
        if hasattr(self.file, "seek"):
            try:
                self.file.seek(0)
            except (AttributeError, IOError) as e:
                logger.warning(f"Could not seek file: {str(e)}")
        self.user = user
        self.dry_run = dry_run
        self.import_log: Optional[ImportLog] = None
        self.error_report = None  # Initialize error_report to avoid AttributeError
        self.parser = None
        self.validated_data: List[Dict] = []
        self.errors: List[Dict] = []
        self.row_errors: List[Dict] = []  # Track detailed row errors

    def validate_file(self) -> Tuple[bool, Optional[str]]:
        """
        Validate file format and extension.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not hasattr(self.file, "name"):
            return False, "Invalid file object"

        if not validate_file_extension(self.file.name, self.ALLOWED_EXTENSIONS):
            return (
                False,
                f"Invalid file type. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}",
            )

        return True, None

    def create_import_log(self) -> ImportLog:
        """
        Create import log entry.

        Returns:
            ImportLog instance
        """
        file_type = get_file_type(self.file.name) or "unknown"

        self.import_log = ImportLog.objects.create(
            module_name=self.MODULE_NAME,
            file_name=self.file.name,
            file_type=file_type,
            status="pending",
            created_by=self.user,
        )

        # Initialize error report helper for row-level error tracking
        # self.error_report = ErrorReport(self.import_log)
        return self.import_log

    def parse_file(self) -> Tuple[bool, Optional[str]]:
        """
        Parse the import file.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            file_type = get_file_type(self.file.name)

            if file_type == "excel":
                self.parser = ExcelParser(self.file)
            elif file_type == "csv":
                self.parser = CSVParser(self.file)
            else:
                return (
                    False,
                    f"CSV/EXCEL is not valid for {self.MODULE_NAME} model. Unsupported file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}",
                )

            # Parse file
            try:
                self.parser.parse()
            except Exception as parse_error:
                file_type_upper = file_type.upper() if file_type else "CSV/EXCEL"
                error_str = str(parse_error).lower()
                # Improve error messages for common cases
                if (
                    "no columns" in error_str
                    or "empty" in error_str
                    or "no data" in error_str
                ):
                    error_msg = f"{file_type_upper} is not valid for {self.MODULE_NAME} model. File is empty or has no data rows."
                else:
                    error_msg = f"{file_type_upper} is not valid for {self.MODULE_NAME} model. Failed to parse file: {str(parse_error)}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg

            # Check if file is empty (no rows)
            row_count = self.parser.get_row_count()
            if row_count == 0:
                file_type_upper = file_type.upper() if file_type else "CSV/EXCEL"
                error_msg = f"{file_type_upper} is not valid for {self.MODULE_NAME} model. File is empty (no data rows found)."
                logger.error(error_msg)
                return False, error_msg

            # Log column names for debugging
            column_names = self.parser.get_column_names()
            if not column_names:
                file_type_upper = file_type.upper() if file_type else "CSV/EXCEL"
                error_msg = f"{file_type_upper} is not valid for {self.MODULE_NAME} model. File has no column headers."
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"File columns: {column_names}")
            logger.info(f"Required columns: {self.REQUIRED_COLUMNS}")

            # Validate required columns (case-insensitive check)
            missing_columns = []
            column_names_lower = [c.strip().lower() for c in column_names]
            for req_col in self.REQUIRED_COLUMNS:
                req_col_lower = req_col.strip().lower()
                if req_col_lower not in column_names_lower:
                    missing_columns.append(req_col)

            if missing_columns:
                file_type_upper = file_type.upper() if file_type else "CSV/EXCEL"
                error_msg = f"{file_type_upper} is not valid for {self.MODULE_NAME} model. Missing required columns: {', '.join(missing_columns)}. Required columns: {', '.join(self.REQUIRED_COLUMNS)}"
                logger.error(error_msg)
                return False, error_msg

            # Update import log
            if self.import_log:
                self.import_log.total_rows = self.parser.get_row_count()
                self.import_log.status = "processing"
                self.import_log.save()

            return True, None

        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}")
            return False, f"Failed to parse file: {str(e)}"

    @abstractmethod
    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map Excel/CSV column names to model field names.

        Returns:
            Dictionary mapping column_name -> field_name
        """
        pass

    @abstractmethod
    def get_validators(self) -> Dict[str, List]:
        """
        Get validators for each field.

        Returns:
            Dictionary mapping field_name -> list of validators
        """
        pass

    @abstractmethod
    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.

        Args:
            row_data: Raw row data from file

        Returns:
            Transformed data dictionary
        """
        pass

    @abstractmethod
    def create_model_instance(self, validated_data: Dict) -> Any:
        """
        Create model instance from validated data.

        Args:
            validated_data: Validated and transformed data

        Returns:
            Model instance (not saved)
        """
        pass

    def validate_row(self, row_data: Dict, row_number: int) -> Tuple[bool, List[Dict]]:
        """
        Validate a single row.

        Args:
            row_data: Row data dictionary
            row_number: Row number (1-indexed)

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        field_mapping = self.get_field_mapping()
        validators = self.get_validators()

        # Map column names to field names (case-insensitive matching)
        mapped_data = {}
        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: v
            for k, v in row_data.items()
        }

        for col_name, field_name in field_mapping.items():
            # Try exact match first
            if col_name in row_data:
                mapped_data[field_name] = row_data[col_name]
            else:
                # Try case-insensitive match
                col_name_lower = col_name.strip().lower()
                if col_name_lower in row_data_lower:
                    # Find the original key with correct casing
                    for key in row_data.keys():
                        if key.strip().lower() == col_name_lower:
                            mapped_data[field_name] = row_data[key]
                            break

        # Debug: Log mapping results (only for first data row)
        if row_number == (getattr(self.parser, "header_row", 0) + 2):
            logger.info(
                f"Row {row_number} - Mapped data keys: {list(mapped_data.keys())}"
            )
            logger.info(
                f"Row {row_number} - Validators for fields: {list(validators.keys())}"
            )
            missing_fields = set(validators.keys()) - set(mapped_data.keys())
            if missing_fields:
                logger.warning(
                    f"Row {row_number} - Missing mapped fields: {missing_fields}"
                )

        # Validate each field
        for field_name, field_validators in validators.items():
            value = mapped_data.get(field_name)

            # Debug first data row
            if row_number == (getattr(self.parser, "header_row", 0) + 2):
                logger.debug(
                    f"Validating field '{field_name}' with value: {value} (type: {type(value)})"
                )

            for validator in field_validators:
                try:
                    is_valid, error_message = validator.validate(value, mapped_data)
                    if not is_valid:
                        errors.append(
                            {
                                "field": field_name,
                                "message": error_message,
                                "value": value,
                            }
                        )
                        if row_number == (getattr(self.parser, "header_row", 0) + 2):
                            logger.debug(
                                f"Validation failed for '{field_name}': {error_message}"
                            )
                except Exception as e:
                    logger.error(
                        f"Error in validator {validator.__class__.__name__} for {field_name}: {str(e)}",
                        exc_info=True,
                    )
                    errors.append(
                        {
                            "field": field_name,
                            "message": f"Validator error: {str(e)}",
                            "value": value,
                        }
                    )

        if row_number == (getattr(self.parser, "header_row", 0) + 2):
            logger.info(
                f"Row {row_number} validation result: {len(errors) == 0} valid, {len(errors)} errors"
            )

        return len(errors) == 0, errors

    def validate_all_rows(self) -> Tuple[int, int]:
        """
        Validate all rows in the file.

        Returns:
            Tuple of (valid_count, error_count)
        """
        if not self.parser:
            logger.warning("Parser not initialized")
            return 0, 0

        rows = self.parser.get_rows()
        logger.info(f"Parsed {len(rows)} rows from file")

        if not rows:
            logger.warning("No rows found in parsed file")
            return 0, 0

        valid_count = 0
        error_count = 0

        # Get header row offset from parser to correctly calculate row numbers
        header_row_offset = getattr(self.parser, "header_row", 0)

        for idx, row_data in enumerate(rows, start=1):
            # Calculate actual row number in the file (including header)
            # Data rows start after header, so add 1 to account for header row
            actual_row_number = idx + header_row_offset + 1
            try:
                # Log first data row for debugging
                if actual_row_number == (header_row_offset + 2):
                    logger.info(f"First row data keys: {list(row_data.keys())}")
                    logger.info(f"First row sample: {dict(list(row_data.items())[:3])}")

                is_valid, errors = self.validate_row(row_data, actual_row_number)

                if actual_row_number == (header_row_offset + 2):
                    logger.info(
                        f"First row validation: is_valid={is_valid}, errors={len(errors)}"
                    )
                    if errors:
                        logger.info(f"First row errors: {errors[:2]}")  # First 2 errors

                if is_valid:
                    # Transform and store validated data
                    try:
                        # Add row number to row_data for tracking
                        row_data_with_number = dict(row_data)
                        row_data_with_number["_row_number"] = actual_row_number
                        transformed_data = self.transform_row_data(row_data_with_number)
                        self.validated_data.append(transformed_data)
                        valid_count += 1
                        logger.debug(
                            f"Row {actual_row_number} validated and transformed successfully"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error transforming row {actual_row_number}: {str(e)}"
                        )

                        # Collect transformation error
                        row_error_details = {
                            "row_number": actual_row_number,
                            "errors": [
                                {
                                    "field": "data_transformation",
                                    "message": f"Data transformation error: {str(e)}",
                                    "value": None,
                                }
                            ],
                            "row_data": dict(row_data),
                        }
                        self.row_errors.append(row_error_details)

                        if self.error_report:
                            self.error_report.add_error(
                                row_number=actual_row_number,
                                error_type="validation",
                                field_name=None,
                                error_message=f"Data transformation error: {str(e)}",
                                raw_data=row_data,
                            )
                        error_count += 1
                else:
                    # Record errors
                    logger.debug(
                        f"Row {actual_row_number} has {len(errors)} validation errors"
                    )

                    # Collect row errors with field details
                    row_error_details = {"row_number": actual_row_number, "errors": []}

                    for error in errors:
                        field_name = error.get("field", "unknown")
                        error_message = error.get("message", "Validation failed")
                        error_value = error.get("value", "")

                        row_error_details["errors"].append(
                            {
                                "field": field_name,
                                "message": error_message,
                                "value": str(error_value) if error_value else None,
                            }
                        )

                        if self.error_report:
                            self.error_report.add_error(
                                row_number=actual_row_number,
                                error_type="validation",
                                field_name=field_name,
                                error_message=error_message,
                                raw_data=row_data,
                            )

                    # Add row data for context
                    row_error_details["row_data"] = dict(row_data)
                    self.row_errors.append(row_error_details)
                    error_count += 1
            except Exception as e:
                logger.error(
                    f"Error validating row {actual_row_number}: {str(e)}", exc_info=True
                )

                # Collect unknown error
                row_error_details = {
                    "row_number": actual_row_number,
                    "errors": [
                        {
                            "field": "unknown",
                            "message": f"Validation error: {str(e)}",
                            "value": None,
                        }
                    ],
                    "row_data": dict(row_data),
                }
                self.row_errors.append(row_error_details)

                # Record as unknown error
                if self.error_report:
                    self.error_report.add_error(
                        row_number=actual_row_number,
                        error_type="unknown",
                        field_name=None,
                        error_message=f"Validation error: {str(e)}",
                        raw_data=row_data,
                    )
                error_count += 1

        logger.info(f"Validation complete: {valid_count} valid, {error_count} errors")

        # Debug: If both are 0, something is wrong
        if valid_count == 0 and error_count == 0 and len(rows) > 0:
            logger.error(
                f"WARNING: {len(rows)} rows parsed but 0 valid and 0 errors - validation may not be running!"
            )
            # Try to validate first row manually to see what's happening
            if rows:
                logger.error(f"First row data: {rows[0]}")
                try:
                    first_data_row_number = getattr(self.parser, "header_row", 0) + 2
                    is_valid, errors = self.validate_row(rows[0], first_data_row_number)
                    logger.error(
                        f"Manual validation of first row: valid={is_valid}, errors={len(errors)}"
                    )
                    if errors:
                        logger.error(f"First row errors: {errors}")
                except Exception as e:
                    logger.error(
                        f"Exception during manual validation: {str(e)}", exc_info=True
                    )

        return valid_count, error_count

    def save_data(self) -> tuple[int, int]:
        """
        Save validated data to database.

        Returns:
            Tuple of (saved_count, failed_count)
        """
        if self.dry_run:
            return len(self.validated_data), 0

        if not self.validated_data:
            return 0, 0

        # Get model class from first instance
        first_instance = self.create_model_instance(self.validated_data[0])
        model_class = first_instance.__class__

        # Create all instances
        instances = [self.create_model_instance(data) for data in self.validated_data]

        # Bulk create (with ignore_conflicts to handle duplicates gracefully)
        writer = BulkWriter(model_class, batch_size=self.BATCH_SIZE)
        saved_count, failed_count = writer.bulk_create(instances, ignore_conflicts=True)

        # Log failed records if any
        if failed_count > 0:
            logger.warning(
                f"Failed to save {failed_count} records (likely due to unique constraint violations)"
            )

        return saved_count, failed_count

    def import_data(self) -> Dict[str, Any]:
        """
        Main import method - orchestrates the entire import process.

        Returns:
            Dictionary with import results
        """
        # Step 1: Validate file
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": error,
                "total_rows": 0,
                "success_count": 0,
                "error_count": 0,
            }

        # Step 2: Create import log
        self.create_import_log()

        # Step 3: Parse file
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
            }

        total_rows = self.parser.get_row_count()
        logger.info(f"Total rows in file: {total_rows}")

        # Step 4: Validate all rows
        valid_count, error_count = self.validate_all_rows()
        logger.info(f"Validation results: {valid_count} valid, {error_count} errors")

        # Step 5: Save data (if not dry run)
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        skipped_details = []
        failed_save_count = 0

        if not self.dry_run and valid_count > 0:
            try:
                result = self.save_data()
                # Handle both old format (saved_count, failed_count) and new format (inserted, updated, skipped, failed)
                if len(result) == 4:
                    inserted_count, updated_count, skipped_count, failed_save_count = (
                        result
                    )
                elif len(result) == 2:
                    # Backward compatibility with old format
                    saved_count, failed_save_count = result
                    inserted_count = saved_count
                    updated_count = 0
                    skipped_count = 0
                else:
                    logger.warning(f"Unexpected save_data return format: {result}")
                    inserted_count = result[0] if result else 0
                    failed_save_count = result[-1] if len(result) > 1 else 0

                # Add save failures to error count
                if failed_save_count > 0:
                    logger.warning(
                        f"{failed_save_count} records failed to save (likely duplicates or constraint violations)"
                    )
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}")
                if self.import_log:
                    self.import_log.mark_failed(str(e))
                return {
                    "success": False,
                    "message": f"Error saving data: {str(e)}",
                    "total_rows": total_rows,
                    "total_records": valid_count,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": error_count + valid_count,
                    "success_count": 0,
                    "error_count": error_count + valid_count,
                    "import_log_id": (
                        str(self.import_log.id) if self.import_log else None
                    ),
                }

        # Step 6: Update import log
        if self.import_log:
            if self.error_report:
                self.error_report.update_import_log_summary()
            # Use inserted_count + updated_count for success, error_count + skipped_count + failed_save_count for errors
            total_saved = inserted_count + updated_count
            total_errors = error_count + skipped_count + failed_save_count
            self.import_log.mark_completed(total_saved, total_errors)

        # Determine success: at least some records saved
        is_success = inserted_count > 0 or updated_count > 0

        return {
            "success": is_success,
            "message": f"Import completed: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped, {error_count + failed_save_count} errors",
            "total_rows": total_rows,
            "total_records": valid_count,
            "inserted": inserted_count,
            "updated": updated_count,
            "skipped": skipped_count
            + error_count,  # Include validation errors in skipped
            "success_count": inserted_count + updated_count,
            "error_count": error_count + failed_save_count,
            "import_log_id": str(self.import_log.id) if self.import_log else None,
        }
