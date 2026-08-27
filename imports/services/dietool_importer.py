import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Dict, List

from django.utils import timezone

from die.models import Die, DieTool, DiePress, DieSize
from imports.services.base_importer import BaseImporter
from imports.utils import normalize_string

logger = logging.getLogger(__name__)


class DieToolImporter(BaseImporter):
    MODULE_NAME = "DieTool"
    REQUIRED_COLUMNS = ["Section Number", "Die Number"]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.die_cache = {}
        self.die_size_cache = {}
        self.press_cache = {}
        self.customer_cache = {}
        self.bolster_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Section Number": "die",
            "Die Number": "tool_number",
            "Die Oblique Number": "die_oblique_number",
            "Drawing No": "drawing_no",
            "Die Size": "die_size",
            "Cavity": "die_cavity",
            "Press": "eligible_for_press",
            "First Bolster": "_first_bloster",
            "Second Bolster": "_second_bloster",
            "Third Bolster": "_third_bloster",
            "Actual WT / MTR": "actual_kg",
            "Drawing WT / MTR": "drawing_kg",
            "Extrusion Ratio": "extrusion_ratio",
            "Rack No": "rac_no",
            "Row No": "row_no",
            "Column No": "column_no",
            "Max Die Life (MT)": "max_die_life",
            "Vendor": "vendor",
            "Order Date": "order_date",
            "Received Date": "received_date",
            "Total Running Kg" : "total_running_kg",
            "Purchase Price": "purchase_price",
            "Material Grade": "material_grade",
            "Ownership": "ownership",
            "Customer": "customer",
            "Tool Status": "tool_status",
            "Location": "location",
            "Status": "status",
            "Remarks": "remarks",
        }

    def get_validators(self) -> Dict[str, List]:
        field_names = list(self.get_field_mapping().values())
        return {fn: [] for fn in field_names}

    def _get_value(self, row_data: Dict, col_name: str):
        if col_name in row_data:
            return row_data[col_name]
        col_lower = col_name.strip().lower()
        for k, v in row_data.items():
            if isinstance(k, str) and k.strip().lower() == col_lower:
                return v
        return None

    def _parse_decimal(self, value):
        if value is not None and str(value).strip() not in ("", "nan"):
            try:
                return Decimal(str(value).strip())
            except (InvalidOperation, ValueError):
                return None
        return None

    def _parse_date(self, value):
        if value is None or str(value).strip() in ("", "nan"):
            return None
        if hasattr(value, "date"):
            return value.date()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(str(value).strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _str_or_none(self, value):
        if value is None:
            return None
        s = str(value).strip()
        return s if s and s.lower() != "nan" else None

    def _lookup_die(self, section_number):
        if not section_number or str(section_number).strip() in ("", "nan"):
            return None
        key = normalize_string(str(section_number).strip())
        if key in self.die_cache:
            return self.die_cache[key]
        die = Die.objects.filter(die_number=key, deleted=False).first()
        self.die_cache[key] = die
        if not die:
            logger.warning(f"Die not found: '{key}'")
        return die

    def _lookup_die_size(self, value):
        if not value or str(value).strip() in ("", "nan"):
            return None
        key = str(value).strip().upper()
        if key in self.die_size_cache:
            return self.die_size_cache[key]

        if "X" not in key:
            logger.warning(f"DieSize invalid format (expected HxW e.g. 210X130): '{key}'")
            self.die_size_cache[key] = None
            return None

        parts = key.split("X", 1)
        try:
            height = Decimal(parts[0].strip())
            width = Decimal(parts[1].strip())
        except (InvalidOperation, ValueError):
            logger.warning(f"DieSize could not parse height/width from: '{key}'")
            self.die_size_cache[key] = None
            return None

        die_size = DieSize.objects.filter(diameter=height, thickness=width, deleted=False).first()
        if not die_size:
            die_size = DieSize.objects.create(diameter=height, thickness=width, created_by=self.user)
            logger.info(f"DieSize created: height={height}, width={width}")

        self.die_size_cache[key] = die_size
        return die_size

    def _lookup_press(self, value):
        if not value or str(value).strip() in ("", "nan"):
            return None
        key = str(value).strip().lower()
        if key in self.press_cache:
            return self.press_cache[key]
        press = DiePress.objects.filter(name__iexact=key, deleted=False).first()
        self.press_cache[key] = press
        if not press:
            logger.warning(f"DiePress not found: '{value}'")
        return press

    def _lookup_customer(self, value, vendor_only=False):
        if not value or str(value).strip() in ("", "nan"):
            return None
        key = str(value).strip().lower()
        cache_key = f"vendor:{key}" if vendor_only else key
        if cache_key in self.customer_cache:
            return self.customer_cache[cache_key]
        from customer.models import Customer
        qs = Customer.objects.filter(customer_name__iexact=key, deleted=False)
        if vendor_only:
            qs = qs.filter(company_type__in=["vendor", "customer_vendor"])
        customer = qs.first()
        self.customer_cache[cache_key] = customer
        if not customer:
            logger.warning(f"{'Vendor' if vendor_only else 'Customer'} not found: '{value}'")
        return customer

    def _lookup_bolsters(self, value):
        if not value or str(value).strip() in ("", "nan"):
            return []
        from bloster.models import BlosterMaster
        result = []
        for bn in [b.strip() for b in str(value).split(",") if b.strip()]:
            if bn in self.bolster_cache:
                if self.bolster_cache[bn]:
                    result.append(self.bolster_cache[bn])
            else:
                bolster = BlosterMaster.objects.filter(bloster_no=bn, deleted=False).first()
                self.bolster_cache[bn] = bolster
                if bolster:
                    result.append(bolster)
                else:
                    logger.warning(f"BlosterMaster not found: '{bn}'")
        return result

    def _calc_weight_diff(self, actual_kg, drawing_kg):
        """Return (weight_diff_kg, weight_diff_per) matching DieTool model fields."""
        if actual_kg is not None and drawing_kg is not None and drawing_kg > 0:
            kg_diff = actual_kg - drawing_kg
            percent = (kg_diff / drawing_kg) * Decimal("100")
            return (
                Decimal(str(round(kg_diff, 3))),
                Decimal(str(round(percent, 2))),
            )
        return None, None

    def transform_row_data(self, row_data: Dict) -> Dict:
        g = lambda col: self._get_value(row_data, col)

        die_cavity_raw = g("Cavity")
        try:
            die_cavity = int(Decimal(str(die_cavity_raw).strip())) if die_cavity_raw and str(die_cavity_raw).strip() not in ("", "nan") else 0
        except (InvalidOperation, ValueError):
            die_cavity = 0

        ownership_raw = self._str_or_none(g("Ownership"))
        if ownership_raw:
            ownership_val = ownership_raw.lower()
            ownership = ownership_val if ownership_val in ("own", "customer") else None
        else:
            ownership = None

        tool_status_raw = self._str_or_none(g("Tool Status"))
        valid_statuses = [c[0] for c in DieTool.RUN_UNDER_DEVIATION]
        tool_status = tool_status_raw.lower() if tool_status_raw and tool_status_raw.lower() in valid_statuses else "under development"

        location_raw = self._str_or_none(g("Location"))
        valid_locations = [c[0] for c in DieTool.DIE_TOOL_LOCATION]
        location = location_raw if location_raw and location_raw in valid_locations else "Die_Tool_Room"

        status_raw = self._str_or_none(g("Status"))
        valid_die_statuses = [c[0] for c in DieTool.DIE_TOOL_STATUS]
        status = status_raw if status_raw and status_raw in valid_die_statuses else "Available"

        actual_kg = self._parse_decimal(g("Actual WT / MTR"))
        drawing_kg = self._parse_decimal(g("Drawing WT / MTR"))
        weight_diff_kg, weight_diff_per = self._calc_weight_diff(actual_kg, drawing_kg)

        return {
            "die": self._lookup_die(g("Section Number")),
            "tool_number": self._str_or_none(g("Die Number")),
            "die_oblique_number": self._str_or_none(g("Die Oblique Number")),
            "drawing_no": self._str_or_none(g("Drawing No")),
            "die_size": self._lookup_die_size(g("Die Size")),
            "die_cavity": die_cavity,
            "eligible_for_press": self._lookup_press(g("Press")),
            "_first_bloster": self._lookup_bolsters(g("First Bolster")),
            "_second_bloster": self._lookup_bolsters(g("Second Bolster")),
            "_third_bloster": self._lookup_bolsters(g("Third Bolster")),
            "actual_kg": actual_kg,
            "drawing_kg": drawing_kg,
            "weight_diff_kg": weight_diff_kg,
            "weight_diff_per": weight_diff_per,
            "extrusion_ratio": self._parse_decimal(g("Extrusion Ratio")),
            "rac_no": self._str_or_none(g("Rack No")),
            "row_no": self._str_or_none(g("Row No")),
            "column_no": self._str_or_none(g("Column No")),
            "max_die_life": self._parse_decimal(g("Max Die Life (MT)")),
            "total_running_kg": self._parse_decimal(g("Total Running Kg")),
            "vendor": self._lookup_customer(g("Vendor"), vendor_only=True),
            "order_date": self._parse_date(g("Order Date")),
            "received_date": self._parse_date(g("Received Date")),
            "purchase_price": self._parse_decimal(g("Purchase Price")),
            "material_grade": self._str_or_none(g("Material Grade")),
            "ownership": ownership,
            "customer": self._lookup_customer(g("Customer")),
            "tool_status": tool_status,
            "location": location,
            "status": status,
            "remarks": self._str_or_none(g("Remarks")),
            "created_by": self.user,
            "created_at": timezone.now(),
            "deleted": False,
        }

    def create_model_instance(self, validated_data: Dict) -> DieTool:
        return DieTool(**validated_data)

    def validate_row(self, row_data: Dict, row_number: int) -> tuple[bool, List[Dict]]:
        is_valid, errors = super().validate_row(row_data, row_number)

        section_number = self._get_value(row_data, "Section Number")
        tool_number = self._get_value(row_data, "Die Number")

        if not section_number or str(section_number).strip() in ("", "nan"):
            is_valid = False
            errors.append({
                "field": "die",
                "message": "Section Number is required",
                "value": None,
            })
        elif not self._lookup_die(section_number):
            is_valid = False
            errors.append({
                "field": "die",
                "message": f"Section '{section_number}' not found in database",
                "value": section_number,
            })

        if not tool_number or str(tool_number).strip() in ("", "nan"):
            is_valid = False
            errors.append({
                "field": "tool_number",
                "message": "Die Number is required",
                "value": None,
            })

        return is_valid, errors

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
                is_valid, errors = self.validate_row(row_data, idx)

                if is_valid:
                    transformed = self.transform_row_data(row_data)
                    transformed["_row_number"] = idx
                    transformed["_original_row_data"] = self._serialize_row_data(dict(row_data))
                    self.validated_data.append(transformed)
                    valid_count += 1
                else:
                    error_count += 1
                    self._add_row_error(idx, errors, row_data)

            except Exception as e:
                error_count += 1
                self._add_row_error(idx, [{"field": "unknown", "message": str(e)}], row_data)

        return valid_count, error_count

    def _serialize_row_data(self, row_data: Dict) -> Dict:
        result = {}
        for k, v in row_data.items():
            try:
                import json
                json.dumps(v)
                result[k] = v
            except (TypeError, ValueError):
                result[k] = str(v) if v is not None else None
        return result

    def _add_row_error(self, row_number: int, errors: List[Dict], row_data: Dict):
        if not hasattr(self, "row_errors"):
            self.row_errors = []
        self.row_errors.append({
            "row_number": row_number,
            "errors": [
                {
                    "field": e.get("field", "unknown"),
                    "message": e.get("message", "Validation failed"),
                    "value": str(e.get("value", "")) if e.get("value") is not None else None,
                }
                for e in errors
            ],
            "row_data": self._serialize_row_data(row_data),
        })

    def _save_errors_to_database(self) -> None:
        if not self.import_log or not getattr(self, "row_errors", None):
            return
        from imports.models import ImportErrorRow
        ImportErrorRow.objects.filter(import_log=self.import_log).delete()
        for row in self.row_errors:
            for err in (row.get("errors") or []):
                ImportErrorRow.objects.create(
                    import_log=self.import_log,
                    row_number=row.get("row_number") or 0,
                    error_type="validation",
                    field_name=err.get("field") or "",
                    error_message=str(err.get("message")),
                    raw_data=self._serialize_row_data(row.get("row_data", {})),
                )

    def save_data(self) -> tuple[int, int, int, int, List[Dict]]:
        if not self.validated_data:
            return 0, 0, 0, 0, []

        inserted = updated = skipped = failed = 0
        inserted_rows = []
        audit_fields = {"created_by", "updated_by", "created_at", "updated_at", "deleted"}
        now = timezone.now()

        # Strip metadata
        rows = []
        for data in self.validated_data:
            row_num = data.pop("_row_number", None)
            original_row_data = data.pop("_original_row_data", {})
            first_bloster = data.pop("_first_bloster", [])
            second_bloster = data.pop("_second_bloster", [])
            third_bloster = data.pop("_third_bloster", [])
            rows.append((row_num, original_row_data, first_bloster, second_bloster, third_bloster, data))

        # Tuple: (row_num, original_row_data, first_bloster, second_bloster, third_bloster, data)
        die_ids = list({data["die"].pk for *_, data in rows if data.get("die")})
        existing_map: Dict[tuple, DieTool] = {
            (obj.die_id, obj.tool_number, obj.die_oblique_number): obj
            for obj in DieTool.objects.filter(die_id__in=die_ids, deleted=False)
        }

        to_create: List[DieTool] = []
        to_create_bloster_data: List[tuple] = []
        to_update: List[DieTool] = []
        to_update_bloster_data: List[tuple] = []
        update_fields: set = set()

        for row_num, original_row_data, first_bloster, second_bloster, third_bloster, data in rows:
            try:
                die_obj = data.get("die")
                tool_number = data.get("tool_number")
                die_oblique_number = data.get("die_oblique_number")

                if not die_obj or not tool_number:
                    failed += 1
                    self._add_row_error(
                        row_num or 0,
                        [{"field": "die/tool_number", "message": "Die or Tool Number is missing or invalid"}],
                        original_row_data,
                    )
                    continue

                existing = existing_map.get((die_obj.pk, tool_number, die_oblique_number))

                if existing:
                    needs_update = False
                    for key, new_value in data.items():
                        if key in audit_fields:
                            continue
                        existing_value = getattr(existing, key, None)
                        if isinstance(new_value, Decimal) or isinstance(existing_value, Decimal):
                            if (new_value is None) != (existing_value is None) or (
                                new_value is not None and existing_value is not None
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
                        logger.info(f"Row {row_num}: Exact duplicate → skipped")
                        continue

                    if not self.dry_run:
                        for key, value in data.items():
                            if key not in audit_fields:
                                setattr(existing, key, value)
                                update_fields.add(key)
                        existing.updated_by = self.user
                        existing.updated_at = now
                        to_update.append(existing)
                        to_update_bloster_data.append((existing, first_bloster, second_bloster, third_bloster))

                    updated += 1
                    logger.info(f"Row {row_num}: Updated (die={die_obj.die_number}, tool_number={tool_number})")

                else:
                    if not self.dry_run:
                        create_data = {k: v for k, v in data.items() if k not in audit_fields}
                        instance = DieTool(created_by=self.user, created_at=now, **create_data)
                        to_create.append(instance)
                        to_create_bloster_data.append((first_bloster, second_bloster, third_bloster))

                    inserted += 1
                    if row_num:
                        inserted_rows.append({"row_number": row_num})
                    logger.info(f"Row {row_num}: Inserted (die={die_obj.die_number}, tool_number={tool_number})")

            except Exception as e:
                failed += 1
                self._add_row_error(
                    row_num or 0,
                    [{"field": "save", "message": str(e)}],
                    original_row_data,
                )

        if self.dry_run:
            return inserted, updated, skipped, failed, inserted_rows

        # Bulk create in batches
        created_objs: List[DieTool] = []
        for i in range(0, len(to_create), self.BATCH_SIZE):
            created_objs.extend(
                DieTool.objects.bulk_create(to_create[i: i + self.BATCH_SIZE], ignore_conflicts=False)
            )

        for instance, (first_b, second_b, third_b) in zip(created_objs, to_create_bloster_data):
            if first_b:
                instance.first_bloster.set(first_b)
            if second_b:
                instance.second_bloster.set(second_b)
            if third_b:
                instance.third_bloster.set(third_b)

        # Bulk update in batches
        if to_update and update_fields:
            fields_list = list(update_fields) + ["updated_by", "updated_at"]
            for i in range(0, len(to_update), self.BATCH_SIZE):
                DieTool.objects.bulk_update(to_update[i: i + self.BATCH_SIZE], fields_list)

        for instance, first_b, second_b, third_b in to_update_bloster_data:
            if first_b:
                instance.first_bloster.set(first_b)
            if second_b:
                instance.second_bloster.set(second_b)
            if third_b:
                instance.third_bloster.set(third_b)

        logger.info(f"DieTool import summary: inserted={inserted}, updated={updated}, skipped={skipped}, failed={failed}")
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
                    "import_log_id": str(self.import_log.id) if self.import_log and self.import_log.id else "",
                    "row_errors": [],
                },
            }

        total_rows = self.parser.get_row_count() if self.parser else 0
        valid_count, error_count = self.validate_all_rows()
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")

        if not self.dry_run and hasattr(self, "row_errors") and self.row_errors:
            self._save_errors_to_database()

        inserted_count = updated_count = skipped_count = failed_count = 0
        inserted_rows = []

        if not self.dry_run and valid_count > 0:
            try:
                result = self.save_data()
                if len(result) == 5:
                    inserted_count, updated_count, skipped_count, failed_count, inserted_rows = result
                else:
                    inserted_count, updated_count, skipped_count, failed_count = result[:4]
            except Exception as e:
                logger.error(f"Error saving data: {str(e)}", exc_info=True)
                save_error_count = max(
                    len(getattr(self, "row_errors", []) or []),
                    valid_count + error_count,
                )
                if self.import_log:
                    self.import_log.success_count = 0
                    self.import_log.error_count = save_error_count
                    self.import_log.mark_failed(str(e))
                return {
                    "success": False,
                    "message": f"Error saving data: {str(e)}",
                    "data": {
                        "total_records": total_rows, "inserted": 0, "updated": 0,
                        "skipped": valid_count + error_count, "failed": valid_count + error_count,
                        "success_count": 0, "error_count": save_error_count,
                        "import_log_id": str(self.import_log.id) if self.import_log and self.import_log.id else "",
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
            message_parts.append(f"{skipped_count} record skipped successfully")
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
                "import_log_id": str(self.import_log.id) if self.import_log and self.import_log.id else "",
                "row_errors": [
                    {"row_number": r.get("row_number"), "errors": r.get("errors", [])}
                    for r in row_errors_all
                ],
            },
        }

    def import_data(self) -> Dict[str, Any]:
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": "Excel or csv file not uploaded for this particular model.",
                "data": {
                    "total_records": 0, "inserted": 0, "updated": 0, "skipped": 0,
                    "failed": 0, "success_count": 0, "error_count": 0,
                    "import_log_id": "", "row_errors": [],
                },
            }

        try:
            self.create_import_log()
            logger.info(f"Import log created: ID={self.import_log.id if self.import_log else 'None'}")
        except Exception as e:
            logger.error(f"Error creating import log: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error initializing import: {str(e)}",
                "data": {
                    "total_records": 0, "inserted": 0, "updated": 0, "skipped": 0,
                    "failed": 0, "success_count": 0, "error_count": 0,
                    "import_log_id": "", "row_errors": [],
                },
            }

        return self._run_import()
