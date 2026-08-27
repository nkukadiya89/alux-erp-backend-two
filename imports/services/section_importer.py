import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Dict, List

from django.utils import timezone

from die.models import Die, DieCategory, DieGroup, DieInformation, DieSubCategory
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string

logger = logging.getLogger(__name__)


class DieImporter(BaseImporter):
    """
    Importer for Die (Section) data from CSV/Excel files.
    """

    MODULE_NAME = "Die"
    REQUIRED_COLUMNS = [
        "Section Number",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_die_numbers = set()
        self.die_group_cache = {}
        self.die_category_cache = {}
        self.die_sub_category_cache = {}
        self.customer_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        """
        Updated: CSV headers now use "Section" instead of "Die"
        """
        return {
            "Section Number": "die_number",
            "Customer Reference No": "customer_reference_number",
            "Description": "description",
            "Calculated Kg/Mtr": "wt_kg_p_mt",
            "Dimension 1": "dimension1",
            "Dimension 2": "dimension2",
            "Dimension 3": "dimension3",
            "Dimension 4": "dimension4",
            "Circumscribing Circle Diameter": "ccd_mm",
            "Perimeter Outer": "perimeter_outer",
            "Area Square": "area",
            "Reference Drawing No": "reference_drawing_number",
            "Revision": "revision",
            "Revision Date": "revision_date",
            "Container Size": "container_size",
            "Revision Description" : "revision_description",
            "Front End Process Loss MM": "front_end_process_loss_mm",
            "Back End Process Loss MM": "back_end_process_loss_mm",
            "Stretching Head Loss MM": "stretching_head_loss_mm",
            "Stretching Tail Loss MM": "stretching_tail_loss_mm",
            "Total Process Loss MM": "total_process_loss_mm",
            "Process Description": "process_description",
            "Section Group": "die_group",
            "Section Category": "die_category",
            "Section Subcategory": "die_sub_category",
            "Section Type": "die_type",
            "Ownership Type": "ownership_type",
            "Remarks": "remarks",
            "Customer": "customer",
        }

    def get_validators(self) -> Dict[str, List]:
        """
        Section/Die uses custom validation in validate_row (required fields + DB logic in save_data).
        Return empty validators per field so base validate_row does not run extra checks.
        """
        field_names = list(self.get_field_mapping().values())
        return {fn: [] for fn in field_names}

    def transform_row_data(self, row_data: Dict) -> Dict:
        """
        Transform row data from file format to model format.
        revision, revision_date, container_size go into _die_info (for DieInformation table).
        All other fields go into Die table as before.
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

            if field_name == "die_number":
                if value is not None:
                    if isinstance(value, float) and value.is_integer():
                        value = str(int(value))
                    elif str(value).endswith(".0"):
                        value = str(value)[:-2]
                transformed[field_name] = normalize_string(value) if value else None

            elif field_name in [
                "dimension1",
                "dimension2",
                "dimension3",
                "dimension4",
                "wt_kg_p_mt",
                "stretching_machining_end_loss_mm",
                "tail_end_loss_mm",
                "joint_llh_mm",
                "joint_rhs_mm",
                "total_process_loss_mm",
                "total_process_loss_meter",
                "total_process_loss_kg",
                "front_end_process_loss_mm",
                "back_end_process_loss_mm",
                "stretching_head_loss_mm",
                "stretching_tail_loss_mm",
                "ccd_mm",
                "perimeter_outer",
                "area",
            ]:
                if value is not None and str(value).strip() != "":
                    try:
                        transformed[field_name] = Decimal(str(value).strip())
                    except (InvalidOperation, ValueError):
                        transformed[field_name] = None
                else:
                    transformed[field_name] = None

            elif field_name == "revision":
                transformed[field_name] = str(value).strip() if value is not None and str(value).strip() != "" else None

            elif field_name == "revision_date":
                if value is not None and str(value).strip() != "":
                    if hasattr(value, "date"):
                        transformed[field_name] = value.date()
                    else:
                        parsed = None
                        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
                            try:
                                parsed = datetime.strptime(str(value).strip(), fmt).date()
                                break
                            except ValueError:
                                continue
                        transformed[field_name] = parsed
                else:
                    transformed[field_name] = None

            elif field_name == "container_size":
                if value is not None and str(value).strip() != "":
                    try:
                        transformed[field_name] = int(Decimal(str(value).strip()))
                    except (InvalidOperation, ValueError):
                        transformed[field_name] = None
                else:
                    transformed[field_name] = None

            elif field_name == "die_type":
                value = normalize_string(value).title() if value else None
                if value in [choice[0] for choice in Die.DIE_TYPE]:
                    transformed[field_name] = value
                else:
                    transformed[field_name] = "Solid"

            elif field_name == "die_group":
                if value and str(value).strip():
                    group_name = str(value).strip()
                    group_name_lower = group_name.lower()
                    if group_name_lower in self.die_group_cache:
                        transformed[field_name] = self.die_group_cache[group_name_lower]
                    else:
                        try:
                            group = DieGroup.objects.filter(
                                name__iexact=group_name, deleted=False
                            ).first()
                            if group:
                                self.die_group_cache[group_name_lower] = group
                                transformed[field_name] = group
                            else:
                                logger.warning(f"DieGroup not found in DB: '{group_name}'")
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(f"DieGroup lookup error: {e}")
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None

            elif field_name == "customer":
                ownership_raw = None
                if "Ownership Type" in row_data:
                    ownership_raw = str(row_data["Ownership Type"]).strip().lower().replace(" ", "_").replace("-", "_")

                if ownership_raw == "exclusive":
                    if value and str(value).strip():
                        customer_name = str(value).strip()
                        customer_name_lower = customer_name.lower()
                        if customer_name_lower in self.customer_cache:
                            transformed[field_name] = self.customer_cache[customer_name_lower]
                        else:
                            try:
                                from customer.models import Customer
                                customer = Customer.objects.filter(
                                    customer_name__iexact=customer_name, deleted=False
                                ).first()
                                if customer:
                                    self.customer_cache[customer_name_lower] = customer
                                    transformed[field_name] = customer
                                else:
                                    logger.warning(f"Customer not found in DB: '{customer_name}'")
                                    transformed[field_name] = None
                            except Exception as e:
                                logger.error(f"Customer lookup error: {e}")
                                transformed[field_name] = None
                    else:
                        logger.warning("Ownership is exclusive but Customer value is empty in Excel")
                        transformed[field_name] = None
                else:
                    transformed[field_name] = None

            elif field_name == "customer_reference_number":
                if value is not None and str(value).strip() != "":
                    transformed[field_name] = normalize_string(str(value).strip())
                else:
                    transformed[field_name] = None

            elif field_name == "die_category":
                if value and str(value).strip():
                    category_name = str(value).strip()
                    category_name_lower = category_name.lower()
                    if category_name_lower in self.die_category_cache:
                        transformed[field_name] = self.die_category_cache[category_name_lower]
                    else:
                        try:
                            category = DieCategory.objects.filter(
                                name__iexact=category_name, deleted=False
                            ).first()
                            if category:
                                self.die_category_cache[category_name_lower] = category
                                transformed[field_name] = category
                            else:
                                logger.warning(f"DieCategory not found in DB: '{category_name}'")
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(f"DieCategory lookup error: {e}")
                            transformed[field_name] = None
                else:
                    transformed[field_name] = None

            elif field_name == "ownership_type":
                if value:
                    value = str(value).strip().lower().replace(" ", "_").replace("-", "_")
                    valid_choices = [choice[0] for choice in Die.OWNERSHIP_TYPE]
                    if value in valid_choices:
                        transformed[field_name] = value
                    else:
                        logger.warning(f"ownership_type '{value}' not in choices, defaulting to 'non_exclusive'")
                        transformed[field_name] = "non_exclusive"
                else:
                    transformed[field_name] = "non_exclusive"

            elif field_name == "die_sub_category":
                if value and str(value).strip():
                    sub_category_name = str(value).strip()
                    sub_category_name_lower = sub_category_name.lower()
                    if sub_category_name_lower in self.die_sub_category_cache:
                        transformed[field_name] = self.die_sub_category_cache[sub_category_name_lower]
                    else:
                        try:
                            sub_category = DieSubCategory.objects.filter(
                                name__iexact=sub_category_name, deleted=False
                            ).first()
                            if sub_category:
                                self.die_sub_category_cache[sub_category_name_lower] = sub_category
                                transformed[field_name] = sub_category
                            else:
                                logger.warning(f"DieSubCategory not found in DB: '{sub_category_name}'")
                                transformed[field_name] = None
                        except Exception as e:
                            logger.error(f"DieSubCategory lookup error: {e}")
                            transformed[field_name] = None
                else:
                    if value is not None and str(value).strip() != "":
                        transformed[field_name] = str(value).strip()
                    else:
                        transformed[field_name] = None

            else:
                transformed[field_name] = str(value).strip() if value is not None and str(value).strip() != "" else None

        die_info_data = {
            "revision": transformed.pop("revision", None),
            "revision_date": transformed.pop("revision_date", None),
            "container_size": transformed.pop("container_size", None),
            "reference_drawing_number": transformed.pop("reference_drawing_number", None),
            "revision_description": transformed.pop("revision_description", None),

        }
        transformed["_die_info"] = die_info_data

        wt_kg_p_mt = transformed.get("wt_kg_p_mt")
        if wt_kg_p_mt is not None:
            ten_percent = wt_kg_p_mt * Decimal("0.10")
            transformed["min_wt_kg_p_mt"] = wt_kg_p_mt - ten_percent
            transformed["max_wt_kg_p_mt"] = wt_kg_p_mt + ten_percent
        else:
            transformed["min_wt_kg_p_mt"] = None
            transformed["max_wt_kg_p_mt"] = None

        transformed["created_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["deleted"] = False

        return transformed

    def create_model_instance(self, validated_data: Dict) -> Die:
        """
        Create Die model instance from validated data.
        """
        return Die(**validated_data)

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

    def _save_die_information(self, die_instance: Die, die_info_data: Dict) -> None:
        """
        Create or update DieInformation record linked to the given Die instance.
        Only saves if at least one DieInformation field has a value.
        """
        has_data = any(v is not None for v in die_info_data.values())
        if not has_data:
            return

        existing_info = DieInformation.objects.filter(section=die_instance).first()

        if existing_info:
            for key, value in die_info_data.items():
                setattr(existing_info, key, value)
            existing_info.save()
            logger.info(f"DieInformation updated for die_number={die_instance.die_number}")
        else:
            DieInformation.objects.create(section=die_instance, **die_info_data)
            logger.info(f"DieInformation created for die_number={die_instance.die_number}")

    def validate_row(self, row_data: Dict, row_number: int) -> tuple[bool, List[Dict]]:
        """
        Override base validation to check for duplicates within this import file only.
        Existing database records are handled in save_data for skip/update logic.
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

        required_fields = {
            "die_number": "Section Number",
        }

        for field_name, col_name in required_fields.items():
            value = transformed.get(field_name)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                is_valid = False
                errors.append(
                    {
                        "field": field_name,
                        "message": f"{col_name} is required and cannot be empty",
                        "value": row_data.get(col_name),
                    }
                )

        row_data_lower = {
            k.strip().lower() if isinstance(k, str) else k: (k, v)
            for k, v in row_data.items()
        }

        die_number = None
        if "Section Number" in row_data:
            die_number = row_data["Section Number"]
        else:
            col_name_lower = "section number"
            if col_name_lower in row_data_lower:
                original_key, die_number = row_data_lower[col_name_lower]

        if die_number:
            die_number_normalized = normalize_string(die_number) if die_number else None
            if die_number_normalized:
                self.seen_die_numbers.add(die_number_normalized)

        return is_valid, errors

    def validate_all_rows(self) -> tuple[int, int]:
        """
        Validate all rows.
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
                    idx, [{"field": "unknown", "message": str(e)}], row_data
                )

        return valid_count, error_count

    BATCH_SIZE = 500

    def save_data(self) -> tuple[int, int, int, int, List[Dict]]:
        """
        Bulk-optimised save:
        - Pre-fetch all existing die_numbers in one query.
        - Batch bulk_create for new records.
        - Batch bulk_update for changed records.
        - Batch bulk_create for DieInformation.
        Returns: (inserted, updated, skipped, failed, inserted_rows).
        """
        if not self.validated_data:
            return 0, 0, 0, 0, []

        audit_fields = {"created_by", "updated_by", "created_at", "updated_at", "deleted"}

        rows = []
        for data in self.validated_data:
            row_num = data.pop("_row_number", None)
            original_row_data = data.pop("_original_row_data", {})
            die_info_data = data.pop("_die_info", {})
            rows.append((row_num, original_row_data, die_info_data, data))

        die_numbers = [r[3].get("die_number") for r in rows if r[3].get("die_number")]

        existing_map: Dict[str, Die] = {
            d.die_number: d
            for d in Die.objects.filter(die_number__in=die_numbers, deleted=False)
        }

        inserted = updated = skipped = failed = 0
        inserted_rows: List[Dict] = []

        to_create: List[Die] = []
        to_create_info: List[tuple] = []   
        to_update: List[Die] = []
        to_update_info: List[tuple] = []   
        update_fields: set = set()

        now = timezone.now()

        for row_num, original_row_data, die_info_data, data in rows:
            try:
                die_number = data.get("die_number")
                if not die_number:
                    failed += 1
                    self._add_row_error(
                        row_num or 0,
                        [{"field": "die_number", "message": "Die Number is required"}],
                        original_row_data,
                    )
                    continue

                existing = existing_map.get(die_number)

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
                        to_update_info.append((existing, die_info_data))

                    updated += 1

                else:
                    if not self.dry_run:
                        create_data = {k: v for k, v in data.items() if k not in audit_fields}
                        die_obj = Die(created_by=self.user, created_at=now, **create_data)
                        to_create.append(die_obj)
                        to_create_info.append(die_info_data)

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

        created_objs: List[Die] = []
        for i in range(0, len(to_create), self.BATCH_SIZE):
            batch = to_create[i : i + self.BATCH_SIZE]
            created_objs.extend(Die.objects.bulk_create(batch, ignore_conflicts=False))

        if to_update and update_fields:
            fields_list = list(update_fields) + ["updated_by", "updated_at"]
            for i in range(0, len(to_update), self.BATCH_SIZE):
                batch = to_update[i : i + self.BATCH_SIZE]
                Die.objects.bulk_update(batch, fields_list)

        die_info_to_create: List[DieInformation] = []
        die_info_to_update: List[DieInformation] = []
        die_info_update_fields: set = set()

        for die_obj, die_info_data in zip(created_objs, to_create_info):
            if any(v is not None for v in die_info_data.values()):
                die_info_to_create.append(DieInformation(section=die_obj, **die_info_data))

        if to_update_info:
            existing_info_map = {
                di.section_id: di
                for di in DieInformation.objects.filter(
                    section__in=[d for d, _ in to_update_info]
                )
            }
            for die_obj, die_info_data in to_update_info:
                if not any(v is not None for v in die_info_data.values()):
                    continue
                existing_info = existing_info_map.get(die_obj.pk)
                if existing_info:
                    for key, value in die_info_data.items():
                        setattr(existing_info, key, value)
                        die_info_update_fields.add(key)
                    die_info_to_update.append(existing_info)
                else:
                    die_info_to_create.append(DieInformation(section=die_obj, **die_info_data))

        if die_info_to_create:
            for i in range(0, len(die_info_to_create), self.BATCH_SIZE):
                DieInformation.objects.bulk_create(
                    die_info_to_create[i : i + self.BATCH_SIZE], ignore_conflicts=True
                )

        if die_info_to_update and die_info_update_fields:
            for i in range(0, len(die_info_to_update), self.BATCH_SIZE):
                DieInformation.objects.bulk_update(
                    die_info_to_update[i : i + self.BATCH_SIZE],
                    list(die_info_update_fields),
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