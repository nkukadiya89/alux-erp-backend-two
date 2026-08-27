from typing import Any, Dict, List, Optional

from die.models import DiePress

from ..services.base_importer import BaseImporter
from ..validators.field_validators import LengthFieldValidator, RequiredFieldValidator


class SectionPressImporter(BaseImporter):
    model = DiePress
    unique_field = "code"

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)
        self.validators = [
            RequiredFieldValidator(["code"]),
            LengthFieldValidator(
                {
                    "code": {"max_length": 100, "min_length": 1},
                    "name": {"max_length": 255},
                }
            ),
        ]

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        mapping = {
            "code": "code",
            "Code": "code",
            "Press Code": "code",
            "name": "name",
            "Name": "name",
            "Press Name": "name",
            "capacity": "capacity",
            "Capacity": "capacity",
            "billet_diameter": "billet_diameter",
            "Billet Diameter": "billet_diameter",
            "billet_length_min": "billet_length_min",
            "Billet Length Min": "billet_length_min",
            "billet_length_max": "billet_length_max",
            "Billet Length Max": "billet_length_max",
            "billet_weight": "billet_weight",
            "Billet Weight": "billet_weight",
            "extrusion_length_min": "extrusion_length_min",
            "Extrusion Length Min": "extrusion_length_min",
            "extrusion_length_max": "extrusion_length_max",
            "Extrusion Length Max": "extrusion_length_max",
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
        code = data.get("code")

        if not code or str(code).strip() == "":
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
                            {"row": idx, "reason": "blank data"}
                        )
                    else:
                        result["failed"] += 1
                        result["errors"].append(msg)
                    continue

                try:
                    existing = DiePress.objects.get(code=mapped["code"])
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {"row": idx, "code": mapped["code"]}
                        )
                    else:
                        result["skipped"] += 1
                except DiePress.DoesNotExist:
                    new_instance = DiePress.objects.create(**mapped)
                    result["inserted"] += 1
                    result["inserted_rows"].append(
                        {"row": idx, "id": new_instance.id, "code": mapped["code"]}
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
            nums = [str(x["row"]) for x in result["inserted_rows"]]
            display = ", ".join(nums[:10])
            extra = f"... ({len(nums)} total)" if len(nums) > 10 else ""
            response["success_message"] = f"Newly added rows: Row {display}{extra}"

        if result["errors"]:
            response["errors"] = result["errors"][:20]
            if result["errors"]:
                response["message"] += f" | First error: {result['errors'][0]}"

        return response
