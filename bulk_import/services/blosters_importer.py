import re
from typing import Any, Dict, List, Optional

from bloster.models import BlosterMaster

from ..services.base_importer import BaseImporter
from ..validators.field_validators import LengthFieldValidator, RequiredFieldValidator
from ..validators.reference_validators import DuplicateValidator, ForeignKeyValidator


class BlostersImporter(BaseImporter):
    """BlosterMaster-specific importer"""

    model = BlosterMaster
    unique_field = "bloster_no"
    required_fields = ["bloster_no", "press"]

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)

        self.validators = [
            RequiredFieldValidator(["bloster_no", "press"]),
            LengthFieldValidator(
                {
                    "bloster_no": {"max_length": 100, "min_length": 1},
                }
            ),
            ForeignKeyValidator(
                {"press": {"model": "die.DiePress", "lookup_field": "name"}}
            ),
            DuplicateValidator(BlosterMaster, "bloster_no"),
        ]

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize bloster row data"""
        field_mapping = {
            "bolster_no": "bloster_no",
            "press": "press",
            "Image": "bloster_image",
            "Bloster Image": "bloster_image",
            "Photo": "bloster_image",
            "Picture": "bloster_image",
            "bloster_image": "bloster_image",
            "Autocard": "autocard",
            "Auto Card": "autocard",
            "DWG": "autocard",
            "Drawing": "autocard",
            "CAD": "autocard",
            "autocard": "autocard",
            "PDF": "pdf",
            "Document": "pdf",
            "File": "pdf",
            "pdf": "pdf",
        }

        normalized_row = {}

        for key, value in row.items():
            if key in field_mapping:
                field_name = field_mapping[key]
                normalized_value = self._normalize_field_value(field_name, value)
                if normalized_value is not None:
                    normalized_row[field_name] = normalized_value

        if not normalized_row.get("bloster_no"):
            normalized_row["bloster_no"] = self._generate_bloster_number()

        return normalized_row

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        """Normalize individual field values"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        if field_name == "bloster_no":
            return self._normalize_bloster_no(value_str)
        elif field_name == "press":
            return self._normalize_text(value_str)
        elif field_name in ["bloster_image", "autocard", "pdf"]:
            return self._normalize_file_path(value_str)
        else:
            return value_str

    def _normalize_bloster_no(self, bloster_no: str) -> str:
        """Normalize bloster number"""
        bloster_no = bloster_no.strip().upper()

        bloster_no = re.sub(r"[^\w\-]", "", bloster_no)

        if not bloster_no:
            raise ValueError("Bloster number cannot be empty after normalization")

        return bloster_no

    def _normalize_text(self, text: str) -> str:
        """Normalize text fields"""
        return text.strip()

    def _normalize_press(self, press_name: str) -> str:
        """Normalize press name for database lookup"""
        return " ".join(press_name.split())

    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path/URL"""
        return file_path.strip()

    def _generate_bloster_number(self) -> str:
        """Auto-generate bloster number if not provided"""
        import random
        import string
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = "".join(random.choices(string.digits, k=4))

        return f"BLO{timestamp}{random_suffix}"

    def validate(self, data: Dict[str, Any]):
        pass

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        bloster_no = data.get("bloster_no")

        if not bloster_no or str(bloster_no).strip() == "":
            return False, f"Row {row_num}: skipped (blank data)"

        if not bloster_no:
            return False, f"Row {row_num}: Bloster Number is required"

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
                            {"row_number": idx, "reason": "blank data"}
                        )
                    else:
                        result["failed"] += 1
                        result["errors"].append(msg)
                    continue

                lookup = {self.unique_field: mapped.get(self.unique_field)}
                if not all(lookup.values()):
                    result["errors"].append(
                        f"Row {idx}: Missing required unique field: {self.unique_field}"
                    )
                    continue

                existing = BlosterMaster.objects.filter(**lookup).first()

                if existing:
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {
                                "row_number": idx,
                                self.unique_field: mapped[self.unique_field],
                            }
                        )
                    else:
                        changed = False
                        if "press" in mapped and mapped["press"]:
                            try:
                                from die.models import DiePress

                                press_name = mapped["press"]
                                print(
                                    f"DEBUG UPDATE: Looking for press with name: '{press_name}'"
                                )
                                press_instance = DiePress.objects.get(name=press_name)
                                print(f"DEBUG UPDATE: Found press: {press_instance}")
                                mapped["press"] = press_instance
                            except DiePress.DoesNotExist:
                                try:
                                    press_instance = DiePress.objects.get(
                                        name__iexact=press_name
                                    )
                                    print(
                                        f"DEBUG UPDATE: Found press with case-insensitive match: {press_instance}"
                                    )
                                    mapped["press"] = press_instance
                                except DiePress.DoesNotExist:
                                    all_presses = DiePress.objects.all().values_list(
                                        "name", flat=True
                                    )
                                    print(
                                        f"DEBUG UPDATE: Available presses: {list(all_presses)}"
                                    )
                                    result["failed"] += 1
                                    result["errors"].append(
                                        f"Row {idx}: Press '{mapped['press']}' not found in DiePress"
                                    )
                                    continue

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
                    if "press" in mapped and mapped["press"]:
                        try:
                            from die.models import DiePress

                            press_name = mapped["press"]
                            print(f"DEBUG: Looking for press with name: '{press_name}'")
                            press_instance = DiePress.objects.get(name=press_name)
                            print(f"DEBUG: Found press: {press_instance}")
                            mapped["press"] = press_instance
                        except DiePress.DoesNotExist:
                            try:
                                press_instance = DiePress.objects.get(
                                    name__iexact=press_name
                                )
                                print(
                                    f"DEBUG: Found press with case-insensitive match: {press_instance}"
                                )
                                mapped["press"] = press_instance
                            except DiePress.DoesNotExist:
                                all_presses = DiePress.objects.all().values_list(
                                    "name", flat=True
                                )
                                print(f"DEBUG: Available presses: {list(all_presses)}")
                                result["failed"] += 1
                                result["errors"].append(
                                    f"Row {idx}: Press '{mapped['press']}' not found in DiePress"
                                )
                                continue

                    obj = BlosterMaster.objects.create(
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
        # if result["failed"]: message_parts.append(f"{result['failed']} records failed")

        response = {
            "success": bool(
                result["inserted"] or result["updated"] or result["skipped"]
            ),
            "total_records": total,
            "inserted": result["inserted"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            # "failed": result["failed"],
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
        }

        if result["inserted_rows"]:
            nums = [str(x["row_number"]) for x in result["inserted_rows"]]
            display = ", ".join(nums[:10])
            extra = f"... ({len(nums)} total)" if len(nums) > 10 else ""
            response["success_message"] = f"Newly added rows: Row {display}{extra}"

        # if result["errors"]:
        #     response["errors"] = result["errors"][:20]
        #     if result["errors"]:
        #         response["message"] += f" | First error: {result['errors'][0]}"

        return response
