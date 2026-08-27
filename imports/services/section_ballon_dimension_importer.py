import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from die.models import Die, SectionBallonDimensions
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string

logger = logging.getLogger(__name__)


class SectionBallonDimensionsImporter(BaseImporter):
    """
    Importer for SectionBallonDimensions data from CSV/Excel files.
    Supports merged rows (blank Section Number filled from previous).
    """

    MODULE_NAME = "SectionBallonDimensions"
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_balloon_nos = {}
        self.die_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Map CSV headers to model fields. Added Position X and Position Y.
        """
        return {
            "Section Number": "section",
            "Balloon Dimension No.": "balloon_no",
            "Dimension Type": "dim_type",
            "Nominal Value (mm)": "nominal_value",
            "Plus Tolerance (+) (mm)": "tolerance_plus",
            "Minus Tolerance (-) (mm)": "tolerance_minus",
            "Min. Acceptable Value": "min_value",
            "Max. Acceptable Value": "max_value",
            "Description": "description",
            "Inspection (Yes/No)": "is_inspection",
            "Critical (Yes/No)": "is_critical",
            "Instrument Used For Inspection": "instrument_used_for_inspection",
            "Position X": "pos_x",
            "Position Y": "pos_y",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Return empty validators per field so base validate_row does not run extra checks.
        Custom validation in validate_row.
        """
        field_names = list(self.get_field_mapping().values())
        return {fn: [] for fn in field_names}

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.
        Added pos_x and pos_y as Decimal.
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

            if field_name == "section":
                if isinstance(value, float):
                    value = int(value)  
                die_number = normalize_string(value) if value else None
                if die_number:
                    die_number_lower = die_number.lower()
                    if die_number_lower in self.die_cache:
                        transformed[field_name] = self.die_cache[die_number_lower]
                    else:
                        try:
                            die = Die.objects.filter(
                                die_number__iexact=die_number, deleted=False
                            ).first()
                            if die:
                                self.die_cache[die_number_lower] = die
                                transformed[field_name] = die
                            else:
                                transformed[field_name] = None
                        except Exception:
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name == "balloon_no":
                if value is not None and value != "":
                    try:
                        transformed[field_name] = int(value)
                    except (ValueError, TypeError):
                        transformed[field_name] = None
                else:
                    transformed[field_name] = None
            elif field_name == "nominal_value":
                transformed[field_name] = (
                    str(value).strip() if value not in (None, "") else None
                )

            elif field_name in [
                "tolerance_plus",
                "tolerance_minus",
                "min_value",
                "max_value",
                "pos_x",
                "pos_y",
            ]:
                if value not in (None, ""):
                    try:
                        transformed[field_name] = Decimal(str(value).strip())
                    except (InvalidOperation, ValueError):
                        transformed[field_name] = None
                        transformed.setdefault("_decimal_errors", []).append(
                            {
                                "field": field_name,
                                "col": col_name,
                                "value": value,
                            }
                        )
                else:
                    transformed[field_name] = None
            elif field_name in ["is_inspection", "is_critical"]:
                value_str = normalize_string(value).lower() if value else ""
                if value_str in ["yes", "true", "1"]:
                    transformed[field_name] = True
                elif value_str in ["no", "false", "0"]:
                    transformed[field_name] = False
                else:
                    transformed[field_name] = False
            else:
                transformed[field_name] = normalize_string(value) if value else None

        transformed["created_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> SectionBallonDimensions:
        """
        Create SectionBallonDimensions model instance from validated data.
        """
        return SectionBallonDimensions(**validated_data)

    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
        """Helper to add row error"""
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
                "row_data": row_data,
            }
        )

    def _save_errors_to_database(self) -> None:
        """Persist row errors to ImportErrorRow"""
        if not self.import_log or not getattr(self, "row_errors", None):
            return

        from imports.models import ImportErrorRow

        for row in self.row_errors:
            row_number = row.get("row_number")
            raw_data = row.get("row_data", {})
            errors = row.get("errors") or []

            for err in errors:
                ImportErrorRow.objects.create(
                    import_log=self.import_log,
                    row_number=row_number or 0,
                    error_type="validation",
                    field_name=err.get("field") or "",
                    error_message=str(err.get("message")),
                    raw_data=raw_data,
                )

    def validate_row(self, row_data: Dict, row_number: int) -> tuple[bool, List[Dict]]:
        """
        Custom validation: check required fields, section exists, balloon_no unique per section in file.
        """
        is_valid, errors = super().validate_row(row_data, row_number)

        try:
            transformed = self.transform_row_data(row_data)
        except Exception as e:
            is_valid = False
            errors.append(
                {
                    "field": "transform",
                    "message": f"Error transforming row data: {str(e)}",
                    "value": None,
                }
            )
            return is_valid, errors


        min_value = transformed.get("min_value")
        max_value = transformed.get("max_value")

        if min_value is not None and max_value is not None:
            if min_value > max_value:
                is_valid = False
                errors.append(
                    {
                        "field": "min_value",
                        "message": "Min. Acceptable Value cannot be greater than Max. Acceptable Value",
                        "value": min_value,
                    }
                )

        section_number = row_data.get("Section Number")
        balloon_no = transformed.get("balloon_no")
        if section_number and balloon_no is not None:
            section_number_normalized = normalize_string(section_number).lower()
            if section_number_normalized not in self.seen_balloon_nos:
                self.seen_balloon_nos[section_number_normalized] = set()
            if balloon_no in self.seen_balloon_nos[section_number_normalized]:
                is_valid = False
                errors.append(
                    {
                        "field": "balloon_no",
                        "message": f"Duplicate Balloon Dimension No. {balloon_no} for Section Number {section_number} within the file",
                        "value": balloon_no,
                    }
                )
            else:
                self.seen_balloon_nos[section_number_normalized].add(balloon_no)

        # Report when Position X / Position Y (or other decimal fields) have non-numeric values
        for item in transformed.pop("_decimal_errors", []):
            is_valid = False
            errors.append(
                {
                    "field": item["field"],
                    "message": f"{item['col']} must be a valid number (got non-numeric value)",
                    "value": item["value"],
                }
            )

        return is_valid, errors

    def validate_all_rows(self) -> tuple[int, int]:
        """
        Validate all rows with support for merged/blank Section Number cells.
        """
        if not self.parser:
            return 0, 0

        rows = self.parser.get_rows()
        if not rows:
            return 0, 0

        valid_count = 0
        error_count = 0
        last_section = None

        for idx, row_data in enumerate(rows, start=2):
            try:
                section_raw = row_data.get("Section Number")
                section_value = ""
                if section_raw is not None:
                    raw_str = str(section_raw).strip()
                    try:
                        section_value = str(int(float(raw_str)))
                    except (ValueError, TypeError):
                        section_value = raw_str

                if not section_value:
                    if last_section:
                        row_data["Section Number"] = last_section
                else:
                    last_section = section_value

                transformed = self.transform_row_data(row_data)

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
                self._add_row_error(
                    idx,
                    [{"field": "unknown", "message": f"Processing error: {str(e)}"}],
                    row_data,
                )

        return valid_count, error_count

    BATCH_SIZE = 500

    def save_data(self) -> tuple[int, int, int, int, List[Dict]]:
        """
        Bulk-optimised save for SectionBallonDimensions.
        - Single bulk fetch of all existing (section_id, balloon_no) pairs.
        - Batch bulk_create for new records.
        - Batch bulk_update for changed records.
        Returns: (inserted, updated, skipped, failed, inserted_rows).
        """
        if not self.validated_data:
            return 0, 0, 0, 0, []

        audit_fields = {"created_by", "updated_by", "created_at", "updated_at", "deleted"}

        # Strip metadata
        rows = []
        for data in self.validated_data:
            row_num = data.pop("_row_number", None)
            original_row_data = data.pop("_original_row_data", {})
            rows.append((row_num, original_row_data, data))

        # Collect all (section_id, balloon_no) pairs for bulk fetch
        section_balloon_pairs = [
            (r[2]["section"].pk, r[2]["balloon_no"])
            for r in rows
            if r[2].get("section") and r[2].get("balloon_no") is not None
        ]
        section_ids = list({p[0] for p in section_balloon_pairs})

        # Single query to fetch all relevant existing records
        existing_map: Dict[tuple, SectionBallonDimensions] = {
            (obj.section_id, obj.balloon_no): obj
            for obj in SectionBallonDimensions.objects.filter(
                section_id__in=section_ids, deleted=False
            )
        }

        inserted = updated = skipped = failed = 0
        inserted_rows: List[Dict] = []
        to_create: List[SectionBallonDimensions] = []
        to_update: List[SectionBallonDimensions] = []
        update_fields: set = set()
        now = timezone.now()

        for row_num, original_row_data, data in rows:
            try:
                section = data.get("section")
                balloon_no = data.get("balloon_no")
                if not section or balloon_no is None:
                    skipped += 1
                    continue

                existing = existing_map.get((section.pk, balloon_no))

                if existing:
                    needs_update = False
                    for key, new_value in data.items():
                        if key in audit_fields:
                            continue
                        existing_value = getattr(existing, key, None)
                        if isinstance(new_value, Decimal) or isinstance(existing_value, Decimal):
                            if (new_value is None) != (existing_value is None) or (
                                new_value is not None
                                and existing_value is not None
                                and new_value != existing_value
                            ):
                                needs_update = True
                                break
                        elif hasattr(new_value, "pk"):
                            if getattr(new_value, "pk", None) != getattr(existing_value, "pk", None):
                                needs_update = True
                                break
                        elif new_value != existing_value:
                            needs_update = True
                            break

                    if not needs_update:
                        skipped += 1
                        continue

                    if not self.dry_run:
                        for key, value in data.items():
                            if key not in audit_fields:
                                setattr(existing, key, value)
                                update_fields.add(key)
                        existing.updated_by = self.user
                        existing.updated_at = now
                        to_update.append(existing)

                    updated += 1

                else:
                    if not self.dry_run:
                        create_data = {k: v for k, v in data.items() if k not in audit_fields}
                        to_create.append(
                            SectionBallonDimensions(created_by=self.user, created_at=now, **create_data)
                        )
                    inserted += 1
                    if row_num:
                        inserted_rows.append({"row_number": row_num})

            except Exception as e:
                failed += 1
                self._add_row_error(
                    row_num or 0,
                    [{"field": "save", "message": str(e)}],
                    original_row_data,
                )

        if self.dry_run:
            return inserted, updated, skipped, failed, inserted_rows

        for i in range(0, len(to_create), self.BATCH_SIZE):
            SectionBallonDimensions.objects.bulk_create(
                to_create[i : i + self.BATCH_SIZE], ignore_conflicts=False
            )

        if to_update and update_fields:
            fields_list = list(update_fields) + ["updated_by", "updated_at"]
            for i in range(0, len(to_update), self.BATCH_SIZE):
                SectionBallonDimensions.objects.bulk_update(
                    to_update[i : i + self.BATCH_SIZE], fields_list
                )

        logger.info(
            f"Summary: inserted={inserted}, updated={updated}, skipped={skipped}, failed={failed}"
        )
        return inserted, updated, skipped, failed, inserted_rows

    def _run_import(self) -> Dict[str, Any]:
        """Core import logic — assumes import_log already exists."""
        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            return {
                "success": False,
                "message": error,
                "data": {
                    "total_records": 0, "inserted": 0, "updated": 0,
                    "skipped": 0, "failed": 0, "success_count": 0,
                    "error_count": 0,
                    "import_log_id": str(self.import_log.id) if self.import_log else "",
                    "row_errors": [],
                },
            }

        total_rows = self.parser.get_row_count() if self.parser else 0
        valid_count, error_count = self.validate_all_rows()

        if not self.dry_run and getattr(self, "row_errors", None):
            self._save_errors_to_database()

        inserted_count = updated_count = skipped_count = failed_count = 0
        inserted_rows: List[Dict] = []

        if not self.dry_run and valid_count > 0:
            try:
                inserted_count, updated_count, skipped_count, failed_count, inserted_rows = self.save_data()
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}", exc_info=True)
                if self.import_log:
                    self.import_log.mark_failed(str(e))
                return {
                    "success": False,
                    "message": f"Error saving data: {str(e)}",
                    "data": {
                        "total_records": total_rows, "inserted": 0, "updated": 0,
                        "skipped": 0, "failed": valid_count + error_count,
                        "success_count": 0, "error_count": valid_count + error_count,
                        "import_log_id": str(self.import_log.id) if self.import_log else "",
                        "row_errors": [
                            {"row_number": r.get("row_number"), "errors": r.get("errors", [])}
                            for r in (getattr(self, "row_errors", []) or [])
                        ],
                    },
                }

        failed_count += error_count

        if self.import_log:
            self.import_log.mark_completed(inserted_count + updated_count, failed_count)
            self.import_log.refresh_from_db()

        message_parts = []
        if inserted_count:
            message_parts.append(f"{inserted_count} records inserted successfully")
        if updated_count:
            message_parts.append(f"{updated_count} records updated successfully")
        if skipped_count:
            message_parts.append(f"{skipped_count} records skipped")
        if failed_count:
            message_parts.append(f"{failed_count} records failed")

        row_errors_all = getattr(self, "row_errors", []) or []
        return {
            "success": bool(inserted_count > 0 or updated_count > 0 or skipped_count > 0),
            "message": " | ".join(message_parts) if message_parts else "No records processed",
            "data": {
                "total_records": total_rows,
                "inserted": inserted_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "success_count": inserted_count + updated_count,
                "error_count": failed_count,
                "import_log_id": str(self.import_log.id) if self.import_log else "",
                "row_errors": [
                    {"row_number": r.get("row_number"), "errors": r.get("errors", [])}
                    for r in row_errors_all[:5]
                ],
            },
        }

    def import_data(self) -> Dict[str, Any]:
        """Synchronous import — validates file, creates log, then runs import."""
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": "Excel or csv file not uploaded for this particular model.",
                "data": {
                    "total_records": 0, "inserted": 0, "updated": 0,
                    "skipped": 0, "failed": 0, "success_count": 0,
                    "error_count": 0, "import_log_id": "", "row_errors": [],
                },
            }

        try:
            self.create_import_log()
        except Exception as e:
            logger.error(f"Error creating import log: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error initializing import: {str(e)}",
                "data": {
                    "total_records": 0, "inserted": 0, "updated": 0,
                    "skipped": 0, "failed": 0, "success_count": 0,
                    "error_count": 0, "import_log_id": "", "row_errors": [],
                },
            }

        return self._run_import()
