from typing import Any, Dict, List, Optional

from customer.models import CustomerType

from ..services.base_importer import BaseImporter
from ..validators.field_validators import LengthFieldValidator, RequiredFieldValidator


class CustomerTypeImporter(BaseImporter):
    model = CustomerType
    unique_field = "name"

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)
        self.validators = [
            RequiredFieldValidator(["name"]),
            LengthFieldValidator({"name": {"max_length": 255, "min_length": 2}}),
        ]

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        mapping = {
            "Name": "name",
            "Customer Type Name": "name",
            "Customer Type": "name",
            "Type Name": "name",
            "Type": "name",
            "name": "name",
        }

        normalized = {}
        for k, v in row.items():
            if k in mapping:
                val = v
                if val is not None and str(val).strip() == "":
                    val = None
                normalized[mapping[k]] = val

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
                    existing = CustomerType.objects.get(name=mapped["name"])
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {"row": idx, "name": mapped["name"]}
                        )
                    else:
                        result["skipped"] += 1
                except CustomerType.DoesNotExist:
                    new_instance = CustomerType.objects.create(**mapped)
                    result["inserted"] += 1
                    result["inserted_rows"].append(
                        {"row": idx, "id": new_instance.id, "name": mapped["name"]}
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
