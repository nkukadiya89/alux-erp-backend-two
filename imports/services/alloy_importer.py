import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from imports.parsers.csv_parser import CSVParser
from imports.parsers.excel_parser import ExcelParser
from imports.services.base_importer import BaseImporter
from imports.utils import get_file_type
from product.models import Alloy, StandardMaster

logger = logging.getLogger(__name__)


class AlloyImporter(BaseImporter):
    MODULE_NAME = "Alloy"
    REQUIRED_COLUMNS = [
        "Alloy Code",
        "Standard Name",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    unique_fields = ["alloy_code", "standard"]

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.standard_name_cache = {}  

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Alloy Code": "alloy_code",
            "Standard Name": "standard",
            "Color Code": "color_code",
            "Remark": "remark",
            "Si Min": "si_min",
            "Si Max": "si_max",
            "SI Min": "si_min",
            "SI Max": "si_max",
            "Mg Min": "mg_min",
            "Mg Max": "mg_max",
            "MG Min": "mg_min",
            "MG Max": "mg_max",
            "Fe Min": "fe_min",
            "Fe Max": "fe_max",
            "FE Min": "fe_min",
            "FE Max": "fe_max",
            "Mn Min": "mn_min",
            "Mn Max": "mn_max",
            "MN Min": "mn_min",
            "MN Max": "mn_max",
            "Cu Min": "cu_min",
            "Cu Max": "cu_max",
            "CU Min": "cu_min",
            "CU Max": "cu_max",
            "Zn Min": "zn_min",
            "Zn Max": "zn_max",
            "ZN Min": "zn_min",
            "ZN Max": "zn_max",
            "Cr Min": "cr_min",
            "Cr Max": "cr_max",
            "CR Min": "cr_min",
            "CR Max": "cr_max",
            "Ti Min": "ti_min",
            "Ti Max": "ti_max",
            "TI Min": "ti_min",
            "TI Max": "ti_max",
            "Bi Min": "bi_min",
            "Bi Max": "bi_max",
            "BI Min": "bi_min",
            "BI Max": "bi_max",
            "Pb Min": "pb_min",
            "Pb Max": "pb_max",
            "PB Min": "pb_min",
            "PB Max": "pb_max",
            "Sn Min": "sn_min",
            "Sn Max": "sn_max",
            "SN Min": "sn_min",
            "SN Max": "sn_max",
            "Al Min": "al_min",
            "Al Max": "al_max",
            "AL Min": "al_min",
            "AL Max": "al_max",
            "Others Each Min": "others_each_min",
            "Others Each Max": "others_each_max",
            "Others Total Min": "others_total_min",
            "Others Total Max": "others_total_max",
        }

    DECIMAL_FIELDS = {
        "si_min",
        "si_max",
        "mg_min",
        "mg_max",
        "fe_min",
        "fe_max",
        "mn_min",
        "mn_max",
        "cu_min",
        "cu_max",
        "zn_min",
        "zn_max",
        "cr_min",
        "cr_max",
        "ti_min",
        "ti_max",
        "bi_min",
        "bi_max",
        "pb_min",
        "pb_max",
        "sn_min",
        "sn_max",
        "others_each_min",
        "others_each_max",
        "others_total_min",
        "others_total_max",
        "al_min",
        "al_max",
    }

    def get_validators(self) -> Dict[str, List]:
        return {}

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        if field_name in ["alloy_code", "standard", "color_code", "remark"]:
            return value_str

        try:
            return Decimal(str(value_str))
        except (InvalidOperation, ValueError):
            return None

    def transform_row_data(self, row_data: Dict) -> Dict:
        field_mapping = self.get_field_mapping()
        normalized_row = {}
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

            normalized_value = self._normalize_field_value(field_name, value)
            normalized_row[field_name] = normalized_value

            if field_name == "standard":
                if value and str(value).strip():
                    standard_name = str(value).strip()
                    standard_name_lower = standard_name.lower()
                    
                    if standard_name_lower in self.standard_name_cache:
                        transformed[field_name] = self.standard_name_cache[standard_name_lower]
                    else:
                        try:
                            # First try to find existing (case-insensitive)
                            standard = StandardMaster.objects.filter(
                                name__iexact=standard_name
                            ).first()
                            
                            if not standard:
                                # Create if not found
                                standard, _ = StandardMaster.objects.get_or_create(
                                    name=standard_name  # exact match on create
                                )
                                logger.info(f"Created new StandardMaster: '{standard_name}'")
                            
                            self.standard_name_cache[standard_name_lower] = standard
                            transformed[field_name] = standard
                            
                        except Exception as e:
                            logger.error(f"Error: {str(e)}", exc_info=True)
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None

        normalized_row.update(transformed)
        return normalized_row

    def create_model_instance(self, validated_data: Dict) -> Alloy:
        return Alloy(**validated_data)

    def parse_file(self):
        try:
            file_type = get_file_type(self.file.name)
            if file_type == "excel":
                self.parser = ExcelParser(self.file)
            elif file_type == "csv":
                self.parser = CSVParser(self.file)
            else:
                return (
                    False,
                    "Excel or csv file not uploaded for this particular model.",
                )

            self.parser.parse()
            column_names = self.parser.get_column_names()

            field_mapping = self.get_field_mapping()
            column_names_lower = [c.strip().lower() for c in column_names]

            # Debug logging
            logger.info(f"CSV columns found: {column_names}")
            logger.info(f"CSV columns (lowercase): {column_names_lower}")
            logger.info(
                f"Expected columns: {list(field_mapping.keys())[:10]}..."
            )  # Show first 10

            found_column = any(
                col_name.strip().lower() in column_names_lower
                for col_name in field_mapping.keys()
            )

            # Debug which columns matched
            matched_columns = [
                col_name
                for col_name in field_mapping.keys()
                if col_name.strip().lower() in column_names_lower
            ]
            logger.info(f"Matched columns: {matched_columns}")
            logger.info(f"Found any match: {found_column}")

            if not found_column:
                logger.error(f"Missing required column. File columns: {column_names}")
                return (
                    False,
                    "Excel or csv file not uploaded for this particular model.",
                )

            if self.import_log:
                self.import_log.total_rows = self.parser.get_row_count()
                self.import_log.status = "processing"
                self.import_log.save()

            return True, None
        except Exception as e:
            logger.error(f"Failed to parse file: {str(e)}", exc_info=True)
            return False, "Excel or csv file not uploaded for this particular model."

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        if not data.get("alloy_code"):
            return False, f"Row {row_num}: Alloy Code is required"

        min_max_pairs = [
            ("si_min", "si_max", "Si"),
            ("mg_min", "mg_max", "Mg"),
            ("fe_min", "fe_max", "Fe"),
            ("mn_min", "mn_max", "Mn"),
            ("cu_min", "cu_max", "Cu"),
            ("zn_min", "zn_max", "Zn"),
            ("cr_min", "cr_max", "Cr"),
            ("ti_min", "ti_max", "Ti"),
            ("bi_min", "bi_max", "Bi"),
            ("pb_min", "pb_max", "Pb"),
            ("sn_min", "sn_max", "Sn"),
            ("others_each_min", "others_each_max", "Others Each"),
            ("others_total_min", "others_total_max", "Others Total"),
            ("al_min", "al_max", "Al"),
        ]

        return True, None

    def _is_exact_duplicate(self, instance, data):
        for field, new_val in data.items():
            if field in [
                "_row_number",
                "_original_row_data",
                "id",
                "created_by",
                "updated_by",
                "created_at",
                "updated_at",
                "deleted",
                "deleted_at",
            ]:
                continue
            old_val = getattr(instance, field, None)
            if self._normalize_field_value(
                field, old_val
            ) != self._normalize_field_value(field, new_val):
                return False
        return True

    def validate_all_rows(self) -> tuple[int, int]:
        if not self.parser:
            return 0, 0

        rows = self.parser.get_rows()
        if not rows:
            return 0, 0

        valid_count = 0
        error_count = 0

        for idx, row_data in enumerate(rows, start=2):
            try:
                field_mapping = self.get_field_mapping()
                for col_name, field_name in field_mapping.items():
                    if field_name not in self.DECIMAL_FIELDS:
                        continue

                    raw_val = None
                    if col_name in row_data:
                        raw_val = row_data.get(col_name)
                    else:
                        for k in row_data.keys():
                            if (
                                isinstance(k, str)
                                and k.strip().lower() == col_name.strip().lower()
                            ):
                                raw_val = row_data.get(k)
                                break

                    if raw_val is None or (
                        isinstance(raw_val, str) and raw_val.strip() == ""
                    ):
                        continue

                    try:
                        dec_val = Decimal(str(raw_val).strip())
                    except (InvalidOperation, ValueError):
                        error_count += 1
                        self._add_row_error(
                            idx,
                            [
                                {
                                    "field": field_name,
                                    "message": f"Row {idx}: {col_name} must be a number",
                                    "value": raw_val,
                                }
                            ],
                            row_data,
                        )
                        raise ValueError("invalid_decimal")
                    frac_digits = max(-dec_val.as_tuple().exponent, 0)
                    if frac_digits > 3:
                        error_count += 1
                        self._add_row_error(
                            idx,
                            [
                                {
                                    "field": field_name,
                                    "message": f"Row {idx}: {col_name} must have at most 3 decimal places",
                                    "value": raw_val,
                                }
                            ],
                            row_data,
                        )
                        raise ValueError("invalid_decimal")

                    t = dec_val.as_tuple()
                    total_digits = len(t.digits)
                    exp = t.exponent
                    if exp > 0:
                        int_digits = total_digits + exp
                    else:
                        int_digits = max(total_digits - frac_digits, 0)

                    if int_digits > 3:
                        error_count += 1
                        self._add_row_error(
                            idx,
                            [
                                {
                                    "field": field_name,
                                    "message": f"Row {idx}: {col_name} must have at most 3 digits before the decimal point",
                                    "value": raw_val,
                                }
                            ],
                            row_data,
                        )
                        raise ValueError("invalid_decimal")
                    if dec_val > Decimal("100"):
                        error_count += 1
                        self._add_row_error(
                            idx,
                            [
                                {
                                    "field": field_name,
                                    "message": f"Row {idx}: {col_name} must be less than or equal to 100",
                                    "value": raw_val,
                                }
                            ],
                            row_data,
                        )
                        raise ValueError("invalid_decimal")

                mapped = self.transform_row_data(row_data)

                def _has_any(fields) -> bool:
                    for f in fields:
                        v = mapped.get(f)
                        if v is None:
                            continue
                        if isinstance(v, str) and v.strip() == "":
                            continue
                        return True
                    return False

                has_min_values = _has_any(Alloy.AL_COMPONENT_MIN_FIELDS)
                has_max_values = _has_any(Alloy.AL_COMPONENT_MAX_FIELDS)

                if has_min_values:
                    sum_min = sum(
                        (Decimal(str(v)) if v is not None and v != "" else Decimal("0"))
                        for v in [mapped.get(f) for f in Alloy.AL_COMPONENT_MIN_FIELDS]
                    )
                    if sum_min > Decimal("100"):
                        error_count += 1
                        self._add_row_error(
                            idx,
                            [
                                {
                                    "field": "validation",
                                    "message": f"Row {idx}: Sum of all Min fields cannot exceed 100.",
                                    "value": None,
                                }
                            ],
                            row_data,
                        )
                        raise ValueError("invalid_sum")

                if has_max_values:
                    sum_max = sum(
                        (Decimal(str(v)) if v is not None and v != "" else Decimal("0"))
                        for v in [mapped.get(f) for f in Alloy.AL_COMPONENT_MAX_FIELDS]
                    )
                    if sum_max > Decimal("100"):
                        error_count += 1
                        self._add_row_error(
                            idx,
                            [
                                {
                                    "field": "validation",
                                    "message": f"Row {idx}: Sum of all Max fields cannot exceed 100.",
                                    "value": None,
                                }
                            ],
                            row_data,
                        )
                        raise ValueError("invalid_sum")

                valid, msg = self._validate_row(mapped, idx)

                if not valid:
                    error_count += 1
                    self._add_row_error(
                        idx,
                        [{"field": "validation", "message": msg, "value": None}],
                        row_data,
                    )
                    continue

                if mapped.get("standard") is None:
                    original_standard = row_data.get("Standard Name") or row_data.get("standard name")

                    error_count += 1
                    self._add_row_error(
                        idx,
                        [
                            {
                                "field": "standard",
                                "message": f"Row {idx}: Standard '{original_standard}' does not exist for this alloy",
                                "value": original_standard,
                            }
                        ],
                        row_data,
                    )
                    continue
                lookup = {f: mapped.get(f) for f in self.unique_fields}
                if not all(lookup.values()):
                    error_count += 1
                    self._add_row_error(
                        idx,
                        [
                            {
                                "field": "validation",
                                "message": f"Row {idx}: Missing required unique fields",
                                "value": None,
                            }
                        ],
                        row_data,
                    )
                    continue

                mapped["_row_number"] = idx
                mapped["_original_row_data"] = dict(row_data)
                self.validated_data.append(mapped)
                valid_count += 1

            except Exception as e:
                if str(e) == "invalid_decimal":
                    continue
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

    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
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

    def save_data(self) -> tuple[int, int, int, int, List[Dict]]:
        if not self.validated_data:
            return 0, 0, 0, 0, []

        inserted = 0
        updated = 0
        skipped = 0
        failed = 0
        inserted_rows = []

        for data in self.validated_data:
            try:
                lookup = {f: data.get(f) for f in self.unique_fields}
                if not all(lookup.values()):
                    failed += 1
                    continue

                existing = Alloy.objects.filter(**lookup, deleted=False).first()
                row_num = data.get("_row_number")
                original_row_data = data.get("_original_row_data", {})

                if existing:
                    if self._is_exact_duplicate(existing, data):
                        skipped += 1
                    else:
                        changed = False
                        for k, v in data.items():
                            if k in [
                                "_row_number",
                                "_original_row_data",
                                "created_by",
                                "updated_by",
                                "created_at",
                                "updated_at",
                                "deleted",
                            ]:
                                continue
                            old_val = getattr(existing, k, None)
                            if self._normalize_field_value(
                                k, old_val
                            ) != self._normalize_field_value(k, v):
                                setattr(existing, k, v)
                                changed = True
                        if changed:
                            if not self.dry_run:
                                existing.save()
                            updated += 1
                        else:
                            skipped += 1
                else:
                    if not self.dry_run:
                        Alloy.objects.create(
                            **{
                                k: v
                                for k, v in data.items()
                                if k not in ["_row_number", "_original_row_data"]
                            },
                            created_by=self.user,
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
            return {
                "success": False,
                "message": error,
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
