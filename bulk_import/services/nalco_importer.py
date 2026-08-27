from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from nalco.models import NalcoMaster

from ..services.base_importer import BaseImporter
from ..validators.field_validators import LengthFieldValidator, RequiredFieldValidator
from ..validators.reference_validators import DuplicateValidator


class NalcoImporter(BaseImporter):
    model = NalcoMaster
    unique_field = "ignot_grade"

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)

        self.validators = [
            RequiredFieldValidator(["ignot_grade", "date", "rate"]),
            LengthFieldValidator({"ignot_grade": {"max_length": 100, "min_length": 1}}),
            DuplicateValidator(NalcoMaster, ["ignot_grade", "date"]),
        ]

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        mapping = {
            "date": "date",
            "Date": "date",
            "ignot_grade": "ignot_grade",
            "Ignot Grade": "ignot_grade",
            "Grade": "ignot_grade",
            "rate": "rate",
            "Rate": "rate",
            "rate_per_mt": "rate_per_mt",
            "Rate / MT": "rate_per_mt",
            "Rate Per MT": "rate_per_mt",
            "difference": "difference",
            "Difference": "difference",
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

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        """Normalize individual field values"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        if field_name == "ignot_grade":
            return value_str

        if field_name == "date":
            date_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"]
            for fmt in date_formats:
                try:
                    return datetime.strptime(value_str, fmt).date()
                except ValueError:
                    continue
            try:
                import pandas as pd

                return pd.to_datetime(value_str).date()
            except:
                return None

        try:
            return Decimal(str(value_str))
        except (InvalidOperation, ValueError):
            return None

    def validate(self, data: Dict[str, Any]):
        pass

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        ignot_grade = data.get("ignot_grade")
        date = data.get("date")
        rate = data.get("rate")

        if (
            (not ignot_grade or str(ignot_grade).strip() == "")
            and (not date or str(date).strip() == "")
            and (not rate or str(rate).strip() == "")
        ):
            return False, f"Row {row_num}: skipped (blank data)"

        if not ignot_grade or str(ignot_grade).strip() == "":
            return False, f"Row {row_num}: Ignot Grade is required"

        if not date:
            return False, f"Row {row_num}: Date is required"

        if rate is None:
            return False, f"Row {row_num}: Rate is required"

        try:
            if Decimal(str(rate)) <= 0:
                return False, f"Row {row_num}: Rate must be greater than 0"
        except (InvalidOperation, ValueError):
            return False, f"Row {row_num}: Invalid rate format"

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
                    existing = NalcoMaster.objects.get(
                        ignot_grade=mapped["ignot_grade"]
                    )
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {"row": idx, "ignot_grade": mapped["ignot_grade"]}
                        )
                    else:
                        result["skipped"] += 1
                except NalcoMaster.DoesNotExist:
                    new_instance = NalcoMaster.objects.create(
                        **mapped, created_by=user, updated_by=user
                    )
                    result["inserted"] += 1
                    result["inserted_rows"].append(
                        {"row_number": idx, "ignot_grade": mapped["ignot_grade"]}
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
