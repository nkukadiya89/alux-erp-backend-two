from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import pandas as pd

from product.models import Alloy

from ..services.base_importer import BaseImporter
from ..validators.field_validators import LengthFieldValidator, RequiredFieldValidator
from ..validators.reference_validators import DuplicateValidator


class AlloyImporter(BaseImporter):
    model = Alloy
    unique_fields = ["alloy_code", "standard_name"]

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)

        self.validators = [
            RequiredFieldValidator(["alloy_code", "standard_name"]),
            LengthFieldValidator(
                {
                    "alloy_code": {"max_length": 50, "min_length": 1},
                    "standard_name": {"max_length": 100, "min_length": 1},
                }
            ),
            DuplicateValidator(Alloy, ["alloy_code", "standard_name"]),
        ]

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize alloy row data"""
        field_mapping = {
            "Alloy Code": "alloy_code",
            "Standard Name": "standard_name",
            "Color Code": "color_code",
            "Remark": "remark",
            "Si Min": "si_min",
            "Si Max": "si_max",
            "Mg Min": "mg_min",
            "Mg Max": "mg_max",
            "Fe Min": "fe_min",
            "Fe Max": "fe_max",
            "Mn Min": "mn_min",
            "Mn Max": "mn_max",
            "Cu Min": "cu_min",
            "Cu Max": "cu_max",
            "Zn Min": "zn_min",
            "Zn Max": "zn_max",
            "Cr Min": "cr_min",
            "Cr Max": "cr_max",
            "Ti Min": "ti_min",
            "Ti Max": "ti_max",
            "Bi Min": "bi_min",
            "Bi Max": "bi_max",
            "Pb Min": "pb_min",
            "Pb Max": "pb_max",
            "Sn Min": "sn_min",
            "Sn Max": "sn_max",
            "Al Min": "al_min",
            "Al Max": "al_max",
            "Others Each Min": "others_each_min",
            "Others Each Max": "others_each_max",
            "Others Total Min": "others_total_min",
            "Others Total Max": "others_total_max",
        }

        normalized_row = {}

        for key, value in row.items():
            if key in field_mapping:
                field_name = field_mapping[key]
                normalized_value = self._normalize_field_value(field_name, value)
                if normalized_value is not None:
                    normalized_row[field_name] = normalized_value

        return normalized_row

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        """Normalize individual field values"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        if field_name in ["alloy_code", "standard_name", "color_code", "remark"]:
            return value_str

        try:
            return Decimal(str(value_str))
        except (InvalidOperation, ValueError):
            return None

    def validate(self, data: Dict[str, Any]):
        pass

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        if not data.get("alloy_code"):
            return False, f"Row {row_num}: Alloy Code is required"

        elements = [
            "si",
            "mg",
            "fe",
            "mn",
            "cu",
            "zn",
            "cr",
            "ti",
            "bi",
            "pb",
            "sn",
            "al",
        ]
        for el in elements:
            min_v = data.get(f"{el}_min")
            max_v = data.get(f"{el}_max")
            if min_v is not None and max_v is not None:
                try:
                    if Decimal(str(min_v)) > Decimal(str(max_v)):
                        return False, f"Row {row_num}: {el.upper()} Min > Max"
                except:
                    pass
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
                    result["failed"] += 1
                    result["errors"].append(msg)
                    continue

                lookup = {f: mapped.get(f) for f in self.unique_fields}
                if not all(lookup.values()):
                    result["failed"] += 1
                    result["errors"].append(
                        f"Row {idx}: Missing required unique fields"
                    )
                    continue

                existing = Alloy.objects.filter(**lookup).first()

                if existing:
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                    else:
                        changed = False
                        for k, v in mapped.items():
                            if self._normalize_field_value(
                                k, getattr(existing, k)
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
                    obj = Alloy.objects.create(
                        **mapped, created_by=user, updated_by=user
                    )
                    result["inserted"] += 1
                    result["inserted_rows"].append({"row_number": idx})

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"Row {idx}: {str(e)}")

        total = len(rows)
        message_parts = []
        if result["inserted"]:
            message_parts.append(f"{result['inserted']} records inserted successfully")
        if result["updated"]:
            message_parts.append(f"{result['updated']} records updated successfully")
        if result["skipped"]:
            message_parts.append(f"{result['skipped']} record skipped successfully")
        if result["failed"]:
            message_parts.append(f"{result['failed']} records failed")

        response = {
            "success": bool(
                result["inserted"] or result["updated"] or result["skipped"]
            ),
            "total_records": total,
            "inserted": result["inserted"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "failed": result["failed"],
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
