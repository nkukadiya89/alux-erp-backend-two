"""
Ageing Cycle Master Bulk Importer

Excel / CSV columns:
    Cycle Name
    Alloy Code
    Alloy Standard
    Temper Code New
    Section Type
    Temper Standard
    Zone1 Temp
    Zone2 Temp
    Zone3 Temp
    Zone4 Temp
    Soaking Time Hrs
    Cooling Type
    Remarks (optional)

Lookup rules:
    Alloy  = Alloy Code + Alloy Standard
    Temper = Alloy Code + Temper Code New + Temper Standard
             + Section Type

    Temper lookup intentionally does NOT require the Temper's
    alloy_id to equal the Alloy resolved from Alloy Code + Alloy Standard.
    This is required because the existing master data contains duplicate
    Alloy Codes across different Alloy Standards.

Important:
    Excel "-", "N/A", "NA", "NULL", "NONE" and blank Section Type
    are treated as NULL. Therefore a Temper with section_type=NULL
    can be matched correctly.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

import pandas as pd
from django.db import IntegrityError, transaction
from django.utils import timezone

from ageing_cycle.models import AgingCycle
from common.models import SectionType
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string
from product.models import Alloy, StandardMaster, Temper
from utils.generate_number import generate_aging_cycle_no

logger = logging.getLogger("imports.ageing_cycle_importer")


class AgeingCycleImporter(BaseImporter):
    MODULE_NAME = "Ageing Cycle"

    REQUIRED_COLUMNS = [
        "Cycle Name",
        "Alloy Code",
        "Alloy Standard",
        "Temper Code New",
        "Temper Standard",
        "Soaking Time Hrs",
        "Cooling Type",
    ]

    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    # Excel/display value -> AgingCycle model choice value
    COOLING_TYPE_MAP = {
        "air cooling": "Air_Cooling",
        "fan cooling": "Fan_Cooling",
        "natural cooling": "Natural_Cooling",
        "water quench": "Water_Quench",
        "water spray cooling": "Water_Spray_Cooling",
        "forced air cooling": "Forced_Air_Cooling",
    }

    @staticmethod
    def _cooling_choices():
        # Keep these values in sync with AgingCycle.COOLING_TYPE_CHOICES.
        return [
            ("Air_Cooling", "Air_Cooling"),
            ("Fan_Cooling", "Fan_Cooling"),
            ("Natural_Cooling", "Natural_Cooling"),
            ("Water_Quench", "Water_Quench"),
            ("Water_Spray_Cooling", "Water_Spray_Cooling"),
            ("Forced_Air_Cooling", "Forced_Air_Cooling"),
        ]

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)

        self.alloy_cache: Dict[Tuple[str, str], Optional[Alloy]] = {}
        self.standard_cache: Dict[str, Optional[StandardMaster]] = {}
        self.section_type_cache: Dict[str, Optional[SectionType]] = {}
        self.temper_cache: Dict[
            Tuple[str, str, str, str],
            Optional[Temper],
        ] = {}

        self.seen_import_keys = set()
        self._skipped_duplicate_count = 0

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Cycle Name": "cycle_name",
            "Alloy Code": "alloy_code",
            "Alloy Standard": "alloy_standard",
            "Temper Code New": "temper_code_new",
            "Section Type": "section_type",
            "Temper Standard": "temper_standard",
            "Zone1 Temp": "zone1_temp",
            "Zone2 Temp": "zone2_temp",
            "Zone3 Temp": "zone3_temp",
            "Zone4 Temp": "zone4_temp",
            "Soaking Time Hrs": "soaking_time",
            "Cooling Type": "cooling_type",
            "Remarks": "remarks",
        }

    def get_validators(self) -> Dict[str, List]:
        return {
            field_name: []
            for field_name in self.get_field_mapping().values()
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clean(self, value):
        """
        Normalize Excel values.

        "-" is especially important for Section Type because the UI
        displays NULL Section Type as "-".
        """
        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        value = str(value).strip()

        if not value:
            return None

        if value.upper() in {
            "-",
            "N/A",
            "NA",
            "NULL",
            "NONE",
            "NAN",
        }:
            return None

        return value

    def _normalize(self, value):
        value = self._clean(value)

        if not value:
            return None

        return normalize_string(value).strip().lower()

    def _normalize_standard(self, value):
        """
        Normalize standard names for comparison.

        Excel/database may contain different dash characters or spacing:
            IS 733 - 1983
            IS 733 – 1983
            IS 733-1983
        These should be treated as the same standard.
        """
        value = self._clean(value)

        if not value:
            return None

        value = str(value).strip().lower()

        for dash in ("–", "—", "‑", "−"):
            value = value.replace(dash, "-")

        value = " ".join(value.split())
        value = value.replace(" - ", "-")
        value = value.replace("- ", "-")
        value = value.replace(" -", "-")

        return value

    def _get_row_value(self, row_data: Dict, column_name: str):
        """
        Read a column case-insensitively so Excel header spacing/case
        does not break the import.
        """
        if column_name in row_data:
            return row_data[column_name]

        target = column_name.strip().lower()

        for key, value in row_data.items():
            if isinstance(key, str) and key.strip().lower() == target:
                return value

        return None

    def _to_decimal(self, value, field_name: str):
        value = self._clean(value)

        if value is None:
            return None

        try:
            decimal_value = Decimal(str(value))

            if decimal_value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

            return decimal_value

        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(
                f"Invalid numeric value '{value}' for {field_name}"
            )

    def _normalize_cooling_type(self, value):
        value = self._clean(value)

        if not value:
            return None

        normalized = value.lower()

        if normalized in self.COOLING_TYPE_MAP:
            return self.COOLING_TYPE_MAP[normalized]

        valid_values = dict(self._cooling_choices())

        # Accept DB value directly.
        if value in valid_values:
            return value

        # Also accept DB value case-insensitively.
        for db_value in valid_values:
            if db_value.lower() == normalized:
                return db_value

        raise ValueError(
            f"Invalid Cooling Type '{value}'. "
            f"Allowed values: {', '.join(valid_values.keys())}"
        )

    # ------------------------------------------------------------------
    # Reference lookup
    # ------------------------------------------------------------------

    def _resolve_alloys(
        self,
        alloy_code: str,
        alloy_standard: str,
    ) -> List[Alloy]:
        """
        Return ALL active Alloy records matching Alloy Code + Standard.

        Important:
        Existing data contains duplicate Alloy master rows with the same
        code/standard. Therefore .get() / .first() alone is unsafe.
        """
        requested_code = self._clean(alloy_code)
        requested_standard = self._normalize_standard(alloy_standard)

        if not requested_code or not requested_standard:
            return []

        candidates = (
            Alloy.objects
            .select_related("standard")
            .filter(
                alloy_code__iexact=str(requested_code).strip(),
                deleted=False,
            )
            .order_by("id")
        )

        return [
            alloy
            for alloy in candidates
            if self._normalize_standard(
                alloy.standard.name if alloy.standard else None
            ) == requested_standard
        ]

    def _resolve_alloy(
        self,
        alloy_code: str,
        alloy_standard: str,
    ) -> Optional[Alloy]:
        """
        Return the first active matching Alloy.

        Kept for compatibility. Temper resolution should use
        _resolve_alloys() because duplicate Alloy master records exist.
        """
        key = (
            self._normalize(alloy_code),
            self._normalize_standard(alloy_standard),
        )

        if key in self.alloy_cache:
            return self.alloy_cache[key]

        alloys = self._resolve_alloys(
            alloy_code,
            alloy_standard,
        )

        alloy = alloys[0] if alloys else None
        self.alloy_cache[key] = alloy
        return alloy

    def _resolve_standard(self, standard_name: str):
        """
        Kept for compatibility/reference. Temper lookup below uses
        standard__name directly because Temper.standard is a FK.
        """
        key = self._normalize(standard_name)

        if key in self.standard_cache:
            return self.standard_cache[key]

        standard = (
            StandardMaster.objects
            .filter(name__iexact=str(standard_name).strip())
            .first()
        )

        self.standard_cache[key] = standard
        return standard

    def _resolve_section_type(
        self,
        section_type_name: Optional[str],
    ):
        # NULL / "-" Section Type means DB section_type=NULL.
        section_type_name = self._clean(section_type_name)

        if not section_type_name:
            return None

        key = self._normalize(section_type_name)

        if key in self.section_type_cache:
            return self.section_type_cache[key]

        section_type = (
            SectionType.objects
            .filter(
                name__iexact=section_type_name.strip(),
                is_archived=False,
            )
            .first()
        )

        self.section_type_cache[key] = section_type
        return section_type

    def _resolve_temper(
        self,
        alloy_code: str,
        temper_code_new: str,
        section_type_name: Optional[str],
        temper_standard: str,
    ) -> Optional[Temper]:
        """
        Resolve Temper from Excel values.

        IMPORTANT:
        Do NOT use alloy_id for Temper lookup.

        Matching rule:
            1. Alloy Code
            2. Temper Code New
            3. Temper Standard
            4. Section Type

        Section Type:
            blank / "-" / "N/A" / "NULL" / "NONE"
            => section_type IS NULL

        Example:
            19500 + O + IS 733 - 1983 + NULL

        must find the Temper record:
            Alloy Code = 19500
            Temper Code = O
            Temper Standard = IS 733 - 1983
            Section Type = NULL
        """

        alloy_code = self._clean(alloy_code)
        temper_code_new = self._clean(temper_code_new)
        section_type_name = self._clean(section_type_name)
        temper_standard = self._clean(temper_standard)

        # ----------------------------------------------------------
        # Cache key
        # ----------------------------------------------------------
        cache_key = (
            self._normalize(alloy_code),
            self._normalize(temper_code_new),
            self._normalize(section_type_name) or "",
            self._normalize_standard(temper_standard),
        )

        if cache_key in self.temper_cache:
            return self.temper_cache[cache_key]

        # ----------------------------------------------------------
        # Required lookup values
        # ----------------------------------------------------------
        if (
            not alloy_code
            or not temper_code_new
            or not temper_standard
        ):
            self.temper_cache[cache_key] = None
            return None

        requested_alloy_code = (
            str(alloy_code).strip().casefold()
        )

        requested_temper_code = (
            str(temper_code_new).strip().casefold()
        )

        requested_standard = self._normalize_standard(
            temper_standard
        )

        requested_section_type = (
            self._normalize(section_type_name) or ""
        )

        # ----------------------------------------------------------
        # IMPORTANT:
        # Only filter by Temper Code at DB level.
        #
        # We intentionally DO NOT use:
        #     alloy_id=alloy.id
        #
        # We also do not rely on the Alloy Standard here.
        # The user requirement is:
        #
        # Alloy Code + Temper Code + Temper Standard
        # + Section Type
        # ----------------------------------------------------------
        candidates = (
            Temper.objects
            .select_related(
                "alloy",
                "standard",
                "section_type",
            )
            .filter(
                temper_code_new__iexact=str(
                    temper_code_new
                ).strip(),
                deleted=False,
            )
            .order_by("id")
        )

        logger.debug(
            "Resolving Temper | alloy_code=%s | temper_code=%s | "
            "temper_standard=%s | section_type=%s | candidates=%s",
            alloy_code,
            temper_code_new,
            temper_standard,
            section_type_name,
            candidates.count(),
        )

        # ----------------------------------------------------------
        # Match every candidate manually.
        #
        # This is intentionally done in Python because the project
        # contains duplicate Alloy master records with the same
        # Alloy Code but different Alloy Standards.
        # ----------------------------------------------------------
        for candidate in candidates:

            # ------------------------------------------------------
            # 1. Alloy Code
            # ------------------------------------------------------
            candidate_alloy_code = None

            if candidate.alloy:
                candidate_alloy_code = self._clean(
                    candidate.alloy.alloy_code
                )

            if not candidate_alloy_code:
                continue

            if (
                str(candidate_alloy_code).strip().casefold()
                != requested_alloy_code
            ):
                continue

            # ------------------------------------------------------
            # 2. Temper Code New
            # ------------------------------------------------------
            candidate_temper_code = self._clean(
                candidate.temper_code_new
            )

            if not candidate_temper_code:
                continue

            if (
                str(candidate_temper_code).strip().casefold()
                != requested_temper_code
            ):
                continue

            # ------------------------------------------------------
            # 3. Temper Standard
            # ------------------------------------------------------
            candidate_standard = (
                candidate.standard.name
                if candidate.standard
                else None
            )

            candidate_standard_normalized = (
                self._normalize_standard(
                    candidate_standard
                )
            )

            if (
                candidate_standard_normalized
                != requested_standard
            ):
                continue

            # ------------------------------------------------------
            # 4. Section Type
            # ------------------------------------------------------
            candidate_section_type = (
                candidate.section_type.name
                if candidate.section_type
                else None
            )

            candidate_section_normalized = (
                self._normalize(candidate_section_type)
                or ""
            )

            if (
                candidate_section_normalized
                != requested_section_type
            ):
                continue

            # ------------------------------------------------------
            # MATCH FOUND
            # ------------------------------------------------------
            self.temper_cache[cache_key] = candidate

            logger.info(
                "TEMPER MATCH FOUND | "
                "Temper ID=%s | Alloy ID=%s | Alloy Code=%s | "
                "Temper Code=%s | Temper Standard=%s | "
                "Section Type=%s",
                candidate.id,
                candidate.alloy_id,
                candidate_alloy_code,
                candidate_temper_code,
                candidate_standard,
                candidate_section_type,
            )

            return candidate

        # ----------------------------------------------------------
        # No matching Temper
        # ----------------------------------------------------------
        logger.warning(
            "TEMPER NOT FOUND | Alloy Code=%s | Temper Code=%s | "
            "Temper Standard=%s | Section Type=%s",
            alloy_code,
            temper_code_new,
            temper_standard,
            section_type_name or "NULL",
        )

        self.temper_cache[cache_key] = None
        return None

    # ------------------------------------------------------------------
    # Transformation
    # ------------------------------------------------------------------

    def transform_row_data(self, row_data: Dict) -> Dict:
        return {
            "cycle_name": self._clean(
                self._get_row_value(row_data, "Cycle Name")
            ),

            "alloy_code": self._clean(
                self._get_row_value(row_data, "Alloy Code")
            ),

            "alloy_standard": self._clean(
                self._get_row_value(row_data, "Alloy Standard")
            ),

            "temper_code_new": self._clean(
                self._get_row_value(row_data, "Temper Code New")
            ),

            "section_type": self._clean(
                self._get_row_value(row_data, "Section Type")
            ),

            "temper_standard": self._clean(
                self._get_row_value(row_data, "Temper Standard")
            ),

            # Zone temperatures are now TEXT
            "zone1_temp": self._clean(
                self._get_row_value(row_data, "Zone1 Temp")
            ),

            "zone2_temp": self._clean(
                self._get_row_value(row_data, "Zone2 Temp")
            ),

            "zone3_temp": self._clean(
                self._get_row_value(row_data, "Zone3 Temp")
            ),

            "zone4_temp": self._clean(
                self._get_row_value(row_data, "Zone4 Temp")
            ),

            "soaking_time": self._clean(
                self._get_row_value(row_data, "Soaking Time Hrs")
            ),

            "cooling_type": self._normalize_cooling_type(
                self._get_row_value(row_data, "Cooling Type")
            ),

            "remarks": self._clean(
                self._get_row_value(row_data, "Remarks")
            ),
        }

    # ------------------------------------------------------------------
    # Error logging
    # ------------------------------------------------------------------

    def _add_error_to_log(
        self,
        row_number,
        error_type,
        field_name,
        error_message,
        raw_data,
    ):
        """
        Compatibility helper used by this importer.

        BaseImporter/importers in this project use ImportErrorRow for
        persistent row-level errors.
        """
        if not getattr(self, "import_log", None):
            return

        try:
            from imports.models import ImportErrorRow

            ImportErrorRow.objects.create(
                import_log=self.import_log,
                row_number=row_number,
                error_type=error_type,
                field_name=field_name,
                error_message=str(error_message),
                raw_data=(
                    raw_data
                    if isinstance(raw_data, dict)
                    else {}
                ),
            )
        except Exception as exc:
            logger.error(
                "Error creating ImportErrorRow: %s",
                exc,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_all_rows(self) -> tuple[int, int]:
        if not self.parser:
            logger.warning("Parser not initialized")
            return 0, 0

        rows = self.parser.get_rows()
        
        if not rows:
            logger.warning("No rows found in import file")
            return 0, 0

        valid_count = 0
        error_count = 0

        self._skipped_duplicate_count = 0
        self.seen_import_keys = set()
        self.validated_data = []

        for row_number, row_data in enumerate(rows, start=2):
            try:
                data = self.transform_row_data(row_data)
                errors = []

                # Required fields
                required_fields = {
                    "cycle_name": "Cycle Name",
                    "alloy_code": "Alloy Code",
                    "alloy_standard": "Alloy Standard",
                    "temper_code_new": "Temper Code New",
                    "temper_standard": "Temper Standard",
                }

                for field_name, column_name in required_fields.items():
                    value = data.get(field_name)

                    if value is None or (
                        isinstance(value, str)
                        and not value.strip()
                    ):
                        errors.append(
                            {
                                "field": field_name,
                                "message": (
                                    f"{column_name} is required"
                                ),
                                "value": self._get_row_value(
                                    row_data,
                                    column_name,
                                ),
                            }
                        )

                alloy = None
                temper = None

                # ------------------------------------------------------
                # 1. Resolve Alloy EXACTLY by:
                #       Alloy Code + Alloy Standard
                # ------------------------------------------------------
                if (
                    data.get("alloy_code")
                    and data.get("alloy_standard")
                ):
                    alloy = self._resolve_alloy(
                        data["alloy_code"],
                        data["alloy_standard"],
                    )

                    if alloy is None:
                        errors.append(
                            {
                                "field": "alloy",
                                "message": (
                                    f"Alloy "
                                    f"'{data['alloy_code']} - "
                                    f"{data['alloy_standard']}' "
                                    f"not found"
                                ),
                                "value": data["alloy_code"],
                            }
                        )

                # ------------------------------------------------------
                # 2. Resolve Temper by:
                #       Alloy Code
                #       + Temper Code New
                #       + Temper Standard
                #       + Section Type
                #
                # IMPORTANT:
                # Temper lookup intentionally does NOT use alloy_id.
                # ------------------------------------------------------
                if (
                    alloy
                    and data.get("temper_code_new")
                    and data.get("temper_standard")
                ):
                    section_type = data.get("section_type")

                    if section_type:
                        resolved_section_type = (
                            self._resolve_section_type(
                                section_type
                            )
                        )

                        if resolved_section_type is None:
                            errors.append(
                                {
                                    "field": "section_type",
                                    "message": (
                                        f"Section Type "
                                        f"'{section_type}' "
                                        f"not found"
                                    ),
                                    "value": section_type,
                                }
                            )

                    temper = self._resolve_temper(
                        alloy_code=data["alloy_code"],
                        temper_code_new=data["temper_code_new"],
                        section_type_name=section_type,
                        temper_standard=data["temper_standard"],
                    )

                    if temper is None:
                        display_section = (
                            data.get("section_type") or "NULL"
                        )

                        errors.append(
                            {
                                "field": "temper",
                                "message": (
                                    f"Temper "
                                    f"'{data['temper_code_new']}' "
                                    f"with Section Type "
                                    f"'{display_section}' "
                                    f"and Standard "
                                    f"'{data['temper_standard']}' "
                                    f"not found for Alloy Code "
                                    f"'{data['alloy_code']}'."
                                ),
                                "value": data["temper_code_new"],
                            }
                        )



                if errors:
                    error_count += 1

                    self._add_error_to_log(
                        row_number=row_number,
                        error_type="validation",
                        field_name=None,
                        error_message="; ".join(
                            error["message"]
                            for error in errors
                        ),
                        raw_data=row_data,
                    )

                    continue

                # Store resolved FK objects.
                data["alloy"] = alloy
                data["temper"] = temper

                # Remove Excel-only lookup fields.
                data.pop("alloy_code", None)
                data.pop("alloy_standard", None)
                data.pop("temper_code_new", None)
                data.pop("section_type", None)
                data.pop("temper_standard", None)

                # Import duplicate key:
                # Cycle Name + Alloy + Temper
                import_key = (
                    self._normalize(data["cycle_name"]),
                    alloy.id,
                    temper.id,
                )

                if import_key in self.seen_import_keys:
                    self._skipped_duplicate_count += 1
                    continue

                self.seen_import_keys.add(import_key)

                data["_row_number"] = row_number
                data["_original_row_data"] = dict(row_data)

                self.validated_data.append(data)
                valid_count += 1

            except Exception as exc:
                error_count += 1

                logger.error(
                    "Error validating Ageing Cycle row %s: %s",
                    row_number,
                    exc,
                    exc_info=True,
                )

                self._add_error_to_log(
                    row_number=row_number,
                    error_type="validation",
                    field_name=None,
                    error_message=str(exc),
                    raw_data=row_data,
                )

        logger.info(
            "Ageing Cycle validation complete: %s valid, %s errors, "
            "%s duplicates skipped",
            valid_count,
            error_count,
            self._skipped_duplicate_count,
        )

        return valid_count, error_count

    # ------------------------------------------------------------------
    # Model creation
    # ------------------------------------------------------------------

    def create_model_instance(
        self,
        validated_data: Dict,
    ) -> AgingCycle:
        data = {
            key: value
            for key, value in validated_data.items()
            if not key.startswith("_")
        }

        data["cycle_code"] = generate_aging_cycle_no()

        return AgingCycle(**data)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_data(self) -> tuple[int, int, int, int]:
        if not self.validated_data:
            return 0, 0, 0, 0

        # BaseImporter expects dry-run to report validated rows.
        if self.dry_run:
            return len(self.validated_data), 0, 0, 0

        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0

        rows = []

        for original_data in self.validated_data:
            data = dict(original_data)

            row_number = data.pop("_row_number", None)
            original_row_data = data.pop(
                "_original_row_data",
                {},
            )

            rows.append(
                (
                    row_number,
                    original_row_data,
                    data,
                )
            )

        # Existing records are identified by:
        # Cycle Name + Alloy + Temper
        cycle_names = {
            data["cycle_name"]
            for _, _, data in rows
            if data.get("cycle_name")
        }

        alloy_ids = {
            data["alloy"].id
            for _, _, data in rows
            if data.get("alloy")
        }

        temper_ids = {
            data["temper"].id
            for _, _, data in rows
            if data.get("temper")
        }

        existing_records = (
            AgingCycle.objects
            .filter(
                cycle_name__in=cycle_names,
                alloy_id__in=alloy_ids,
                temper_id__in=temper_ids,
                deleted=False,
            )
        )

        existing_map = {
            (
                self._normalize(obj.cycle_name),
                obj.alloy_id,
                obj.temper_id,
            ): obj
            for obj in existing_records
        }

        now = timezone.now()

        # Save row by row so one bad row does not destroy the whole import.
        for row_number, original_row_data, data in rows:
            try:
                key = (
                    self._normalize(data["cycle_name"]),
                    data["alloy"].id,
                    data["temper"].id,
                )

                existing = existing_map.get(key)

                if existing:
                    comparison_fields = [
                        "zone1_temp",
                        "zone2_temp",
                        "zone3_temp",
                        "zone4_temp",
                        "soaking_time",
                        "cooling_type",
                        "remarks",
                    ]

                    changed = False

                    for field_name in comparison_fields:
                        new_value = data.get(field_name)

                        if getattr(existing, field_name) != new_value:
                            setattr(existing, field_name, new_value)
                            changed = True

                    if changed:
                        if hasattr(existing, "updated_by"):
                            existing.updated_by = self.user

                        if hasattr(existing, "updated_at"):
                            existing.updated_at = now

                        existing.save()
                        updated_count += 1
                    else:
                        skipped_count += 1

                    continue

                # New Aging Cycle
                data["created_by"] = self.user
                data["created_at"] = now
                data["updated_by"] = self.user
                data["updated_at"] = now
                data["deleted"] = False

                aging_cycle = self.create_model_instance(data)
                aging_cycle.save()

                existing_map[key] = aging_cycle
                inserted_count += 1

            except IntegrityError as exc:
                failed_count += 1

                self._add_error_to_log(
                    row_number=row_number,
                    error_type="database",
                    field_name=None,
                    error_message=(
                        f"Database constraint violation: {exc}"
                    ),
                    raw_data=original_row_data,
                )

                logger.error(
                    "Row %s IntegrityError: %s",
                    row_number,
                    exc,
                    exc_info=True,
                )

            except Exception as exc:
                failed_count += 1

                self._add_error_to_log(
                    row_number=row_number,
                    error_type="unknown",
                    field_name=None,
                    error_message=str(exc),
                    raw_data=original_row_data,
                )

                logger.error(
                    "Row %s save error: %s",
                    row_number,
                    exc,
                    exc_info=True,
                )

        return (
            inserted_count,
            updated_count,
            skipped_count,
            failed_count,
        )

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------

    def import_data(self) -> Dict:
        result = super().import_data()

        duplicate_count = getattr(
            self,
            "_skipped_duplicate_count",
            0,
        )

        if duplicate_count:
            result["skipped"] = (
                result.get("skipped", 0)
                + duplicate_count
            )

        inserted = result.get("inserted", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("error_count", 0)

        result["message"] = (
            f"{inserted} inserted | "
            f"{updated} updated | "
            f"{skipped} skipped | "
            f"{errors} failed"
        )

        return result
