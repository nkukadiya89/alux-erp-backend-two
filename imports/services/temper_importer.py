import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from common.models import SectionType
from imports.parsers.csv_parser import CSVParser
from imports.parsers.excel_parser import ExcelParser
from imports.services.base_importer import BaseImporter
from imports.utils import get_file_type, normalize_string
from product.models import Alloy, StandardMaster, Temper

logger = logging.getLogger("imports.temper_importer")


class TemperImporter(BaseImporter):
    MODULE_NAME = "Temper"
    REQUIRED_COLUMNS = ["Alloy", "Standard"]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    UNIQUE_FIELDS = [
        "alloy",
        "standard", 
        "temper_code_new",
        "section_type",
        "area",
        "section_thickness_over",
        "section_thickness_upto",
    ]

    DECIMAL_FIELDS = {
        "elongation_50mm_min",
        "elongation_min",
        "hardness",
        "tensile_min",
        "tensile_max",
        "yield_min",
        "yield_max",
        "electrical_conductivity_min",
        "electrical_conductivity_max",
    }

    FK_FIELDS = {"alloy", "section_type", "dimention_unit", "yield_unit", "standard"}

    SKIP_ON_SAVE = {"created_by", "created_at", "updated_by", "updated_at", "deleted"}

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        # Caches to avoid repeated DB hits for same value
        self.alloy_cache: Dict = {}
        self.standard_cache: Dict = {}
        self.section_type_cache: Dict = {}
        self.uom_cache: Dict = {}
        self.yield_unit_cache: Dict = {}

    # ------------------------------------------------------------------
    # Field mapping  (CSV column → model field)
    # ------------------------------------------------------------------
    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Alloy":                       "alloy",
            "Standard":                    "standard",
            "Description":                 "description",
            "Section Type":                "section_type",
            "Area":                        "area",
            "Dimension Unit":              "dimention_unit",
            "Elongation Percent min on 50 mm":         "elongation_50mm_min",
            "Elongation Percent min":              "elongation_min",
            "Hardness":                    "hardness",
            "Section Thickness Over":      "section_thickness_over",
            "Section Thickness Upto":      "section_thickness_upto",
            "Tensile Strength Min":        "tensile_min",
            "Tensile Strength Max":        "tensile_max",
            "Yield Strength Min":          "yield_min",
            "Yield Strength Max":          "yield_max",
            "Unit":                        "yield_unit",
            "Electrical Conducitivity Min": "electrical_conductivity_min",
            "Electrical Conducitivity Max": "electrical_conductivity_max",
            "Temper Code Old":             "temper_code_old",
            "Temper Code New":             "temper_code_new",
            "Heat Treatment":              "heat_treatment",
        }

    def get_validators(self) -> Dict[str, List]:
        return {}

    def create_model_instance(self, validated_data: Dict) -> Temper:
        return Temper(**validated_data)

    # ------------------------------------------------------------------
    # File parsing
    # ------------------------------------------------------------------
    def parse_file(self):
        try:
            file_type = get_file_type(self.file.name)
            if file_type == "excel":
                self.parser = ExcelParser(self.file)
            elif file_type == "csv":
                self.parser = CSVParser(self.file)
            else:
                return False, "Excel or csv file not uploaded for this particular model."

            self.parser.parse()
            column_names = self.parser.get_column_names()
            column_names_lower = [c.strip().lower() for c in column_names]
            field_mapping = self.get_field_mapping()

            matched = any(
                col.strip().lower() in column_names_lower
                for col in field_mapping.keys()
            )
            if not matched:
                return False, "Excel or csv file not uploaded for this particular model."

            if self.import_log:
                self.import_log.total_rows = self.parser.get_row_count()
                self.import_log.status = "processing"
                self.import_log.save()

            return True, None
        except Exception as e:
            logger.error(f"Failed to parse file: {str(e)}", exc_info=True)
            return False, "Excel or csv file not uploaded for this particular model."

    # ------------------------------------------------------------------
    # Row value helpers
    # ------------------------------------------------------------------
    def _get_raw(self, row_data: Dict, col_name: str) -> Any:
        """Get value from row by col_name, fallback to case-insensitive match."""
        if col_name in row_data:
            return row_data[col_name]
        col_lower = col_name.strip().lower()
        for k, v in row_data.items():
            if isinstance(k, str) and k.strip().lower() == col_lower:
                return v
        return None

    def _resolve_alloy(self, alloy_code: str) -> Optional[Alloy]:
        """Lookup alloy by code. Returns None if not found — does NOT create."""
        key = alloy_code.strip().lower()
        if key in self.alloy_cache:
            return self.alloy_cache[key]
        try:
            alloy = Alloy.objects.filter(
                alloy_code__iexact=alloy_code.strip(), deleted=False
            ).first()
            self.alloy_cache[key] = alloy  
            return alloy
        except Exception as e:
            logger.error(f"Error looking up Alloy '{alloy_code}': {str(e)}", exc_info=True)
            return None

    def _resolve_standard(self, standard_name: str) -> Optional[StandardMaster]:
        """Lookup standard. Creates it if it doesn't exist."""
        key = standard_name.strip().lower()
        if key in self.standard_cache:
            return self.standard_cache[key]
        try:
            standard = StandardMaster.objects.filter(
                name__iexact=standard_name.strip()
            ).first()
            if not standard:
                standard = StandardMaster.objects.create(name=standard_name.strip())
                logger.info(f"Created new StandardMaster: '{standard_name}'")
            self.standard_cache[key] = standard
            return standard
        except Exception as e:
            logger.error(f"Error resolving Standard '{standard_name}': {str(e)}", exc_info=True)
            return None

    def _resolve_section_type(self, name: str) -> Optional[SectionType]:
        key = name.strip().lower()
        if key in self.section_type_cache:
            return self.section_type_cache[key]
        try:
            st = SectionType.objects.filter(name__iexact=name.strip(), is_archived=False).first()
            if not st:
                st = SectionType.objects.create(name=name.strip(), is_archived=False)
                logger.info(f"Created SectionType: '{name}'")
            self.section_type_cache[key] = st
            return st
        except Exception as e:
            logger.error(f"Error resolving SectionType '{name}': {str(e)}", exc_info=True)
            return None

    def _resolve_uom(self, uom_name: str):
        key = uom_name.strip().upper()
        if key in self.uom_cache:
            return self.uom_cache[key]
        try:
            from common.models import UOM
            uom = UOM.objects.filter(uom_name__iexact=key, deleted=False, is_active=True).first()

            if not uom:
                uom = UOM.objects.create(uom_name=key, deleted=False, is_active=True)
                logger.info(f"Created new UOM: '{key}'")
            self.uom_cache[key] = uom
            return uom
        except Exception as e:
            logger.error(f"Error looking up UOM '{key}': {str(e)}")
            self.uom_cache[key] = None
            return None

    def _resolve_yield_unit(self, name: str):
        key = name.strip().lower()
        if key in self.yield_unit_cache:
            return self.yield_unit_cache[key]
        try:
            from common.models import YieldUnit
            yu = YieldUnit.objects.filter(name__iexact=name.strip(), deleted=False).first()
            if not yu:
                yu = YieldUnit.objects.create(name=name.strip(), deleted=False)
            self.yield_unit_cache[key] = yu
            return yu
        except Exception as e:
            logger.error(f"Error looking up YieldUnit '{name}': {str(e)}")
            self.yield_unit_cache[key] = None
            return None

    def _to_decimal(self, value) -> Optional[Decimal]:
        if value is None or str(value).strip() == "":
            return None
        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            return None

    # ------------------------------------------------------------------
    # Transform one row → model-ready dict
    # ------------------------------------------------------------------
    def transform_row_data(self, row_data: Dict) -> Dict:
        g = lambda col: self._get_raw(row_data, col)  # shorthand

        transformed = {}

        # --- Alloy (must exist) ---
        raw_alloy = g("Alloy")
        if raw_alloy and str(raw_alloy).strip():
            transformed["alloy"] = self._resolve_alloy(str(raw_alloy).strip())
        else:
            transformed["alloy"] = None

        # --- Standard (auto-create if missing) ---
        raw_standard = g("Standard")
        if raw_standard and str(raw_standard).strip():
            transformed["standard"] = self._resolve_standard(str(raw_standard).strip())
        else:
            transformed["standard"] = None

        # --- Simple string fields ---
        transformed["description"]            = normalize_string(g("Description")) or None
        transformed["area"]                   = normalize_string(g("Area")) or None
        transformed["temper_code_old"]        = normalize_string(g("Temper Code Old")) or None
        transformed["temper_code_new"]        = normalize_string(g("Temper Code New")) or None
        transformed["section_thickness_over"] = normalize_string(g("Section Thickness Over")) or None
        transformed["section_thickness_upto"] = normalize_string(g("Section Thickness Upto")) or None

        # --- Section Type (auto-create if missing) ---
        raw_st = g("Section Type")
        transformed["section_type"] = self._resolve_section_type(normalize_string(raw_st)) if raw_st and str(raw_st).strip() else None

        # --- Dimension Unit (auto-create if missing) ---
        raw_uom = g("Dimension Unit")
        transformed["dimention_unit"] = self._resolve_uom(str(raw_uom)) if raw_uom and str(raw_uom).strip() else None

        # --- Yield Unit (lookup only) ---
        raw_yu = g("Unit")
        transformed["yield_unit"] = self._resolve_yield_unit(str(raw_yu)) if raw_yu and str(raw_yu).strip() else None

        # --- Decimal fields ---
        for col, field in [
             ("Elongation Percent min on 50 mm", "elongation_50mm_min"),
             ("Elongation Percent min",          "elongation_min"),
             ("Hardness",                        "hardness"),
             ("Tensile Strength Min",            "tensile_min"),
             ("Tensile Strength Max",            "tensile_max"),
             ("Yield Strength Min",              "yield_min"),
             ("Yield Strength Max",              "yield_max"),
             ("Electrical Conducitivity Min",     "electrical_conductivity_min"),
             ("Electrical Conducitivity Max",     "electrical_conductivity_max"),
        ]:
            transformed[field] = self._to_decimal(g(col))

        # --- Boolean ---
        raw_ht = g("Heat Treatment")
        if raw_ht and str(raw_ht).strip():
            transformed["heat_treatment"] = str(raw_ht).strip().lower() in ["yes", "true", "1", "y"]
        else:
            transformed["heat_treatment"] = False

        return transformed

    # ------------------------------------------------------------------
    # Validate min/max ranges
    # ------------------------------------------------------------------
    def _validate_min_max_ranges(self, data: Dict, row_num: int) -> List[Dict]:
        errors = []
        pairs = [
            ("tensile_min",                 "tensile_max",                 "Tensile"),
            ("yield_min",                   "yield_max",                   "Yield"),
            ("electrical_conductivity_min", "electrical_conductivity_max", "Electrical Conductivity"),
        ]
        for min_f, max_f, label in pairs:
            mn, mx = data.get(min_f), data.get(max_f)
            if mn is not None and mx is not None:
                try:
                    if float(mn) > float(mx):
                        errors.append({
                            "field": min_f,
                            "message": f"Row {row_num}: {label} min cannot be greater than {label.lower()} max",
                            "value": mn,
                        })
                except (ValueError, TypeError):
                    pass
        return errors

    # ------------------------------------------------------------------
    # Validate all rows
    # ------------------------------------------------------------------
    def validate_all_rows(self) -> Tuple[int, int]:
        if not self.parser:
            return 0, 0

        rows = self.parser.get_rows()
        if not rows:
            return 0, 0

        valid_count = 0
        error_count = 0

        for idx, row_data in enumerate(rows, start=2):
            try:
                transformed = self.transform_row_data(row_data)
                row_errors = []

                # 1. Alloy must exist
                if transformed.get("alloy") is None:
                    raw = self._get_raw(row_data, "Alloy")
                    row_errors.append({
                        "field": "alloy",
                        "message": f"Row {idx}: Alloy '{raw}' not found in database",
                        "value": raw,
                    })

                # 2. Standard must be resolved (should always succeed since we auto-create)
                if transformed.get("standard") is None:
                    raw = self._get_raw(row_data, "Standard")
                    row_errors.append({
                        "field": "standard",
                        "message": f"Row {idx}: Standard '{raw}' could not be resolved",
                        "value": raw,
                    })

                # 3. Min/max range checks
                row_errors.extend(self._validate_min_max_ranges(transformed, idx))

                if row_errors:
                    error_count += 1
                    self._add_row_error(idx, row_errors, row_data)
                    continue

                transformed["_row_number"] = idx
                transformed["_original_row_data"] = dict(row_data)
                self.validated_data.append(transformed)
                valid_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Error validating row {idx}: {str(e)}", exc_info=True)
                self._add_row_error(idx, [{"field": "unknown", "message": f"Row {idx}: {str(e)}", "value": None}], row_data)

        return valid_count, error_count

    # ------------------------------------------------------------------
    # Save validated rows
    # ------------------------------------------------------------------
    def _is_exact_duplicate(self, existing: Temper, data: Dict) -> bool:
        """Returns True if nothing changed."""
        for field, new_val in data.items():
            if field in self.SKIP_ON_SAVE:
                continue
            old_val = getattr(existing, field, None)
            if field in self.FK_FIELDS:
                if (new_val.pk if new_val else None) != (old_val.pk if old_val else None):
                    return False
            else:
                if new_val != old_val:
                    return False
        return True

    def save_data(self) -> Tuple[int, int, int, int, List[Dict]]:
        if not self.validated_data:
            return 0, 0, 0, 0, []

        inserted = updated = skipped = failed = 0
        inserted_rows = []

        for data in self.validated_data:
            row_num = data.pop("_row_number", None)
            original_row_data = data.pop("_original_row_data", {})

            try:
                existing = Temper.objects.filter(
                    alloy=data.get("alloy"),
                    standard=data.get("standard"),
                    temper_code_new=data.get("temper_code_new"),
                    section_type=data.get("section_type"),
                    area=data.get("area"),
                    section_thickness_over=data.get("section_thickness_over"),
                    section_thickness_upto=data.get("section_thickness_upto"),
                    deleted=False,
                ).first()

                if existing:
                    if self._is_exact_duplicate(existing, data):
                        skipped += 1
                        logger.info(f"Row {row_num}: Duplicate → skipped")
                    else:
                        if not self.dry_run:
                            for key, value in data.items():
                                if key not in self.SKIP_ON_SAVE:
                                    setattr(existing, key, value)
                            existing.updated_by = self.user
                            existing.updated_at = timezone.now()
                            existing.save()
                        updated += 1
                        logger.info(f"Row {row_num}: Updated")
                else:
                    if not self.dry_run:
                        Temper.objects.create(
                            **{k: v for k, v in data.items() if k not in {"updated_by", "updated_at"}},
                            created_by=self.user,
                        )
                    inserted += 1
                    if row_num:
                        inserted_rows.append({"row_number": row_num})
                    logger.info(f"Row {row_num}: Inserted")

            except Exception as e:
                failed += 1
                logger.error(f"Row {row_num}: Save failed - {str(e)}", exc_info=True)
                self._add_row_error(
                    row_num or 0,
                    [{"field": "save", "message": str(e), "value": None}],
                    original_row_data,
                )

        logger.info(f"Save done: inserted={inserted}, updated={updated}, skipped={skipped}, failed={failed}")
        return inserted, updated, skipped, failed, inserted_rows

    # ------------------------------------------------------------------
    # Error helpers
    # ------------------------------------------------------------------
    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
        if not hasattr(self, "row_errors"):
            self.row_errors = []
        self.row_errors.append({
            "row_number": row_number,
            "errors": [
                {
                    "field":   e.get("field", "unknown"),
                    "message": e.get("message", "Validation failed"),
                    "value":   str(e["value"]) if e.get("value") is not None else None,
                }
                for e in errors
            ],
        })

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
            raw_data = row.get("row_data") if isinstance(row.get("row_data"), dict) else {}
            for err in (row.get("errors") or [{"field": None, "message": "Validation failed", "value": None}]):
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
                    logger.error(f"Error creating ImportErrorRow row {row_number}: {str(e)}", exc_info=True)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def _build_error_response(self, message: str, log_id: str = "", total_rows: int = 0) -> Dict:
        return {
            "success": False,
            "message": message,
            "data": {
                "total_records": total_rows,
                "inserted": 0, "updated": 0, "skipped": 0, "failed": 0,
                "success_count": 0, "error_count": 0,
                "import_log_id": log_id,
                "row_errors": [],
            },
        }

    def import_data(self) -> Dict[str, Any]:
        is_valid, error = self.validate_file()
        if not is_valid:
            return self._build_error_response("Excel or csv file not uploaded for this particular model.")

        try:
            self.create_import_log()
        except Exception as e:
            logger.error(f"Error creating import log: {str(e)}", exc_info=True)
            return self._build_error_response(f"Error initializing import: {str(e)}")

        log_id = str(self.import_log.id) if self.import_log and self.import_log.id else ""

        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            return self._build_error_response(error, log_id=log_id)

        total_rows = self.parser.get_row_count() if self.parser else 0
        valid_count, error_count = self.validate_all_rows()
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")

        if not self.dry_run and getattr(self, "row_errors", None):
            self._save_errors_to_database()

        inserted_count = updated_count = skipped_count = failed_count = 0
        inserted_rows = []

        if not self.dry_run and valid_count > 0:
            try:
                inserted_count, updated_count, skipped_count, failed_count, inserted_rows = self.save_data()
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}", exc_info=True)
                if self.import_log:
                    self.import_log.mark_failed(str(e))
                return self._build_error_response(f"Error saving data: {str(e)}", log_id=log_id, total_rows=total_rows)

        failed_count += error_count

        if self.import_log:
            self.import_log.mark_completed(inserted_count + updated_count, failed_count)
            self.import_log.refresh_from_db()

        parts = []
        if inserted_count: parts.append(f"{inserted_count} records inserted successfully")
        if updated_count:  parts.append(f"{updated_count} records updated successfully")
        if skipped_count:  parts.append(f"{skipped_count} records skipped")
        if failed_count:   parts.append(f"{failed_count} records failed")

        return {
            "success": bool(inserted_count or updated_count or skipped_count),
            "message": " | ".join(parts) if parts else "No records processed",
            "data": {
                "total_records":  total_rows,
                "inserted":       inserted_count,
                "updated":        updated_count,
                "skipped":        skipped_count,
                "failed":         failed_count,
                "success_count":  inserted_count + updated_count,
                "error_count":    failed_count,
                "import_log_id":  log_id,
                "row_errors":     getattr(self, "row_errors", [])[:10],
            },
        }