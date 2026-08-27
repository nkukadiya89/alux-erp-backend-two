from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from product.models import Temper

from ..services.base_importer import BaseImporter


class TemperImporter(BaseImporter):
    model = Temper
    unique_field = "name"

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        mapping = {
            "name": "name",
            "temper_code_new": "code",
            "section_type": "section_type",
            "area": "area",
            "dimention_unit": "dimention_unit",
            "elongation_50mm_min": "elongation_50mm_min",
            "elongation_min": "elongation_min",
            "hardness": "hardness",
            "section_thickness_over": "section_thickness_over",
            "section_thickness_upto": "section_thickness_upto",
            "tensile_min": "tensile_min",
            "tensile_max": "tensile_max",
            "yield_min": "yield_min",
            "yield_max": "yield_max",
            "yield_unit": "yield_unit",
            "electrical_conductivity_min": "electrical_conductivity_min",
            "electrical_conductivity_max": "electrical_conductivity_max",
            "temper_code_old": "temper_code_old",
            # 'temper_code_new': 'temper_code_new',
        }

        mapping_l = {k.strip().lower(): v for k, v in mapping.items()}

        normalized = {}
        for k, v in row.items():
            key = str(k).strip().lower()
            if key in mapping_l:
                val = v
                if val is not None and str(val).strip() == "":
                    val = None
                normalized[mapping_l[key]] = val

        return normalized

    def validate(self, data: Dict[str, Any]):
        pass

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        name = data.get("name")

        if not name or str(name).strip() == "":
            return False, f"Row {row_num}: skipped (blank data)"

        return True, None

    def _is_exact_duplicate(self, instance, data):
        for field, new_val in data.items():
            if field in [
                "id",
                "created_by",
                "updated_by",
                "created_at",
                "updated_at",
                "deleted",
                "deleted_at",
            ]:
                continue
            old_val = getattr(instance, field)
            if self._normalize_field_value(
                field, old_val
            ) != self._normalize_field_value(field, new_val):
                return False
        return True

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        """Normalize individual field values"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        # Decimal fields
        if field_name in [
            "elongation_50mm_min",
            "elongation_min",
            "hardness",
            "tensile_min",
            "tensile_max",
            "yield_min",
            "yield_max",
            "electrical_conductivity_min",
            "electrical_conductivity_max",
        ]:
            try:
                return Decimal(value_str)
            except (InvalidOperation, ValueError):
                return None

        return value_str

    def process_rows(self, rows: List[Dict], user) -> Dict:
        result = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "inserted_rows": [],
            "skipped_rows": [],
        }

        for idx, row in enumerate(rows, start=2):
            try:
                mapped = self.normalize(row)
                valid, msg = self._validate_row(mapped, idx)
                if not valid:
                    if "blank data" in msg:
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {"row_number": idx, "reason": "blank data"}
                        )
                    else:
                        result["failed"] += 1
                        result["errors"].append(msg)
                    continue

                lookup = {self.unique_field: mapped.get(self.unique_field)}
                existing = Temper.objects.filter(**lookup).first()

                if existing:
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {"row_number": idx, "name": mapped["name"]}
                        )
                    else:
                        changed = False

                        # Resolve section_type FK
                        if "section_type" in mapped and mapped["section_type"]:
                            try:
                                from common.models import SectionType

                                section_type_name = mapped["section_type"]
                                section_type_instance = SectionType.objects.get(
                                    name=section_type_name
                                )
                                mapped["section_type"] = section_type_instance
                            except SectionType.DoesNotExist:
                                try:
                                    section_type_instance = SectionType.objects.get(
                                        name__iexact=section_type_name
                                    )
                                    mapped["section_type"] = section_type_instance
                                except SectionType.DoesNotExist:
                                    result["failed"] += 1
                                    result["errors"].append(
                                        f"Row {idx}: SectionType '{section_type_name}' not found"
                                    )
                                    continue

                        for k, v in mapped.items():
                            if self._normalize_field_value(
                                k, getattr(existing, k, None)
                            ) != self._normalize_field_value(k, v):
                                setattr(existing, k, v)
                                changed = True

                        if changed:
                            existing.updated_by = user
                            existing.save()
                            result["updated"] += 1
                        else:
                            result["skipped"] += 1
                else:
                    # Resolve section_type FK for create
                    if "section_type" in mapped and mapped["section_type"]:
                        try:
                            from common.models import SectionType

                            section_type_name = mapped["section_type"]
                            section_type_instance = SectionType.objects.get(
                                name=section_type_name
                            )
                            mapped["section_type"] = section_type_instance
                        except SectionType.DoesNotExist:
                            try:
                                section_type_instance = SectionType.objects.get(
                                    name__iexact=section_type_name
                                )
                                mapped["section_type"] = section_type_instance
                            except SectionType.DoesNotExist:
                                result["failed"] += 1
                                result["errors"].append(
                                    f"Row {idx}: SectionType '{section_type_name}' not found"
                                )
                                continue

                    new_instance = Temper.objects.create(
                        **mapped, created_by=user, updated_by=user
                    )
                    result["inserted"] += 1
                    result["inserted_rows"].append(
                        {"row_number": idx, "name": mapped["name"]}
                    )

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"Row {idx}: {str(e)}")

        message_parts = []
        if result["inserted"] > 0:
            message_parts.append(f"{result['inserted']} records inserted successfully")
        if result["updated"] > 0:
            message_parts.append(f"{result['updated']} records updated successfully")
        if result["skipped"] > 0:
            message_parts.append(f"{result['skipped']} record skipped successfully")
        if result["failed"] > 0:
            message_parts.append(f"{result['failed']} records failed")

        response = {
            "success": bool(
                result["inserted"] or result["updated"] or result["skipped"]
            ),
            "total_records": len(rows),
            "inserted": result["inserted"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
        }

        if result["inserted_rows"]:
            nums = [str(x["row_number"]) for x in result["inserted_rows"]]
            display = ", ".join(nums[:10])
            extra = f"... ({len(nums)} total)" if len(nums) > 10 else ""
            response["success_message"] = f"Newly added rows: Row {display}{extra}"

        if result["errors"]:
            response["errors"] = result["errors"][:20]
            if result["errors"]:
                response["message"] += f" | First error: {result['errors'][0]}"

        return response
