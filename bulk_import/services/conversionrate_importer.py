import re
from typing import Any, Dict, List, Optional

from django.apps import apps

from ..services.base_importer import BaseImporter


class ConversionRateImporter(BaseImporter):
    """ConversionRate bulk importer - handles line items per customer"""

    model = "die.ConversionRate"
    unique_field = None

    def __init__(self, import_job_id: int):
        super().__init__(import_job_id)
        self.model_class = apps.get_model(self.model)

    def normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize conversion rate row data"""
        field_mapping = {
            "customer": "customer",
            "customer name": "customer",
            "customer_name": "customer",
            "die": "die",
            "die number": "die",
            "die_number": "die",
            "profile number": "die",
            "profile_number": "die",
            "profile_no": "die",
            "profile no": "die",
            "alloy": "alloy",
            "alloy code": "alloy",
            "alloy_code": "alloy",
            "temper": "temper",
            "temper name": "temper",
            "temper_name": "temper",
            "conversion": "conversion",
            "conversion rate": "conversion",
            "rate": "conversion",
            "remarks": "remarks",
            "remark": "remarks",
            "notes": "remarks",
            # New: Add mappings for standard_name and temper_code
            "standard_name": "standard_name",
            "standard name": "standard_name",
            "alloy_standard": "standard_name",
            "alloy_standard_name": "standard_name",
            "temper_code": "temper_code",
            "temper code": "temper_code",
        }

        normalized_row = {}

        for key, value in row.items():
            clean_key = str(key).strip().lower()
            if clean_key in field_mapping:
                field_name = field_mapping[clean_key]
                normalized_value = self._normalize_field_value(field_name, value)
                if normalized_value is not None:
                    normalized_row[field_name] = normalized_value

        return normalized_row

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        """Normalize individual field values"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        value_str = str(value).strip()

        if field_name == "conversion":
            return self._normalize_conversion(value_str)
        # New: Handle standard_name and temper_code as strings
        elif field_name in ["standard_name", "temper_code"]:
            return value_str
        else:
            return value_str

    def _normalize_conversion(self, conversion: str) -> float:
        """Normalize conversion rate to float"""
        try:
            cleaned = re.sub(r"[^\d.]", "", conversion)
            if cleaned:
                return float(cleaned)
        except (ValueError, TypeError):
            pass
        return None

    def validate(self, data: Dict[str, Any]):
        """Skip base validation"""
        pass

    def _validate_row(self, data: Dict, row_num: int) -> tuple[bool, Optional[str]]:
        """Validate required fields"""
        if not data.get("customer"):
            return False, f"Row {row_num}: Customer is required"
        if not data.get("die"):
            return False, f"Row {row_num}: Die is required"
        if not data.get("alloy"):
            return False, f"Row {row_num}: Alloy is required"
        if not data.get("temper"):
            return False, f"Row {row_num}: Temper is required"

        return True, None

    def _is_exact_duplicate(self, existing, mapped):
        """Check if all fields match exactly"""
        for field, new_val in mapped.items():
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
            old_val = getattr(existing, field)
            if self._normalize_field_value(
                field, old_val
            ) != self._normalize_field_value(field, new_val):
                return False
        return True

    def process_rows(self, rows: List[Dict], user) -> Dict:
        """Process conversion rate rows"""
        result = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "inserted_rows": [],
            "skipped_rows": [],
        }

        last_customer = None
        for idx, row in enumerate(rows, start=2):
            try:
                mapped = self.normalize(row)
                if mapped.get("customer"):
                    last_customer = mapped["customer"]
                else:
                    mapped["customer"] = last_customer
                valid, msg = self._validate_row(mapped, idx)
                if not valid:
                    result["skipped"] += 1
                    result["skipped_rows"].append({"row_number": idx, "reason": msg})
                    continue

                # Updated: Build lookup with optional standard_name and temper_code for exact matching
                lookup = {
                    "customer__customer_name": mapped.get("customer"),
                    "die__die_number": mapped.get("die"),
                    "alloy__alloy_code": mapped.get("alloy"),
                    "temper__name": mapped.get("temper"),
                }
                if "standard_name" in mapped:
                    lookup["alloy__standard_name"] = mapped["standard_name"]
                if "temper_code" in mapped:
                    lookup["temper__code"] = mapped[
                        "temper_code"
                    ]  # Assuming Temper has 'code' field

                existing = self.model_class.objects.filter(**lookup).first()

                if existing:
                    if self._is_exact_duplicate(existing, mapped):
                        result["skipped"] += 1
                        result["skipped_rows"].append(
                            {"row_number": idx, "customer": mapped.get("customer")}
                        )
                    else:
                        changed = False

                        if "customer" in mapped and isinstance(mapped["customer"], str):
                            try:
                                from customer.models import Customer

                                customer_name = mapped["customer"]
                                customer_instance = Customer.objects.get(
                                    customer_name=customer_name
                                )
                                mapped["customer"] = customer_instance
                            except Customer.DoesNotExist:
                                try:
                                    customer_instance = Customer.objects.get(
                                        customer_name__iexact=customer_name
                                    )
                                    mapped["customer"] = customer_instance
                                except Customer.DoesNotExist:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"Customer '{customer_name}' not found",
                                        }
                                    )
                                    continue

                        if "die" in mapped and isinstance(mapped["die"], str):
                            try:
                                from die.models import Die

                                die_number = mapped["die"]
                                die_instance = Die.objects.filter(
                                    die_number=die_number
                                ).first()
                                if not die_instance:
                                    try:
                                        die_instance = Die.objects.filter(
                                            die_number__iexact=die_number
                                        ).first()
                                    except:
                                        pass
                                if not die_instance:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"Die '{die_number}' not found",
                                        }
                                    )
                                    continue
                                mapped["die"] = die_instance
                            except Exception as e:
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": f"Error resolving die: {str(e)}",
                                    }
                                )
                                continue

                        if "alloy" in mapped and mapped["alloy"]:
                            try:
                                from product.models import Alloy

                                alloy_raw = str(mapped["alloy"]).strip()

                                # Check if standard_name is provided, if not skip
                                standard_name = mapped.get("standard_name")
                                if not standard_name or not str(standard_name).strip():
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": "Standard Name column is required but empty",
                                        }
                                    )
                                    continue

                                code_match = re.search(r"\d+", alloy_raw)
                                if not code_match:
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {
                                            "row_number": idx,
                                            "reason": f"Invalid alloy format, no numeric code found in '{alloy_raw}'",
                                        }
                                    )
                                    continue
                                alloy_code = code_match.group()

                                # Get standard_name from column
                                standard_name = str(standard_name).strip()

                                # Build filter with alloy_code + standard_name
                                filter_kwargs = {"alloy_code__exact": alloy_code}
                                filter_kwargs["standard_name__iexact"] = standard_name

                                alloy_instance = Alloy.objects.filter(
                                    **filter_kwargs
                                ).first()

                                if not alloy_instance:
                                    reason = f"Alloy code '{alloy_code}'"
                                    if standard_name:
                                        reason += (
                                            f" with standard_name '{standard_name}'"
                                        )
                                    reason += " not found in database"
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {"row_number": idx, "reason": reason}
                                    )
                                    continue

                                mapped["alloy"] = alloy_instance

                            except Exception as e:
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": f"Error resolving alloy: {str(e)}",
                                    }
                                )
                                continue

                        # Updated: Resolve temper with optional temper_code (assuming Temper has 'code' field)
                        if "temper" in mapped and isinstance(mapped["temper"], str):
                            try:
                                from product.models import Temper

                                temper_name = mapped["temper"]
                                temper_code = mapped.get("temper_code")
                                filter_kwargs = {"name__iexact": temper_name}
                                if temper_code:
                                    filter_kwargs["code__iexact"] = temper_code
                                temper_instance = Temper.objects.filter(
                                    **filter_kwargs
                                ).first()
                                if not temper_instance:
                                    reason = f"Temper '{temper_name}'"
                                    if temper_code:
                                        reason += f" with code '{temper_code}'"
                                    reason += " not found"
                                    result["skipped"] += 1
                                    result["skipped_rows"].append(
                                        {"row_number": idx, "reason": reason}
                                    )
                                    continue
                                mapped["temper"] = temper_instance
                            except Exception as e:
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": f"Error resolving temper: {str(e)}",
                                    }
                                )
                                continue

                        # Remove helper fields before updating
                        for k, v in mapped.items():
                            if k not in ["standard_name", "temper_code"]:
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
                            result["skipped_rows"].append(
                                {"row_number": idx, "customer": str(existing.customer)}
                            )
                else:
                    # Create path - similar resolutions
                    if "customer" in mapped and mapped["customer"]:
                        try:
                            from customer.models import Customer

                            customer_name = mapped["customer"]
                            customer_instance = Customer.objects.get(
                                customer_name=customer_name
                            )
                            mapped["customer"] = customer_instance
                        except Customer.DoesNotExist:
                            try:
                                customer_instance = Customer.objects.get(
                                    customer_name__iexact=customer_name
                                )
                                mapped["customer"] = customer_instance
                            except Customer.DoesNotExist:
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": f"Customer '{customer_name}' not found",
                                    }
                                )
                                continue

                    if "die" in mapped and mapped["die"]:
                        try:
                            from die.models import Die

                            die_number = mapped["die"]
                            die_instance = Die.objects.filter(
                                die_number=die_number
                            ).first()
                            if not die_instance:
                                try:
                                    die_instance = Die.objects.filter(
                                        die_number__iexact=die_number
                                    ).first()
                                except:
                                    pass
                            if not die_instance:
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": f"Die '{die_number}' not found",
                                    }
                                )
                                continue
                            mapped["die"] = die_instance
                        except Exception as e:
                            result["skipped"] += 1
                            result["skipped_rows"].append(
                                {
                                    "row_number": idx,
                                    "reason": f"Error resolving die: {str(e)}",
                                }
                            )
                            continue

                    # Updated: Resolve alloy for create with exact matching
                    if "alloy" in mapped and mapped["alloy"]:
                        try:
                            from product.models import Alloy

                            alloy_raw = str(mapped["alloy"]).strip()

                            # Check if standard_name is provided, if not skip
                            standard_name = mapped.get("standard_name")
                            if not standard_name or not str(standard_name).strip():
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": "Standard Name column is required but empty",
                                    }
                                )
                                continue

                            # Extract numeric code
                            code_match = re.search(r"\d+", alloy_raw)
                            if not code_match:
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {
                                        "row_number": idx,
                                        "reason": f"Invalid alloy format, no numeric code found in '{alloy_raw}'",
                                    }
                                )
                                continue
                            alloy_code = code_match.group()

                            # Get standard_name from column
                            standard_name = str(standard_name).strip()

                            # Build filter with alloy_code + standard_name
                            filter_kwargs = {"alloy_code__exact": alloy_code}
                            filter_kwargs["standard_name__iexact"] = standard_name

                            alloy_instance = Alloy.objects.filter(
                                **filter_kwargs
                            ).first()

                            if not alloy_instance:
                                reason = f"Alloy code '{alloy_code}'"
                                if standard_name:
                                    reason += f" with standard_name '{standard_name}'"
                                reason += " not found in database"
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {"row_number": idx, "reason": reason}
                                )
                                continue

                            mapped["alloy"] = alloy_instance

                        except Exception as e:
                            result["skipped"] += 1
                            result["skipped_rows"].append(
                                {
                                    "row_number": idx,
                                    "reason": f"Error resolving alloy: {str(e)}",
                                }
                            )
                            continue

                    # Updated: Resolve temper for create
                    if "temper" in mapped and mapped["temper"]:
                        try:
                            from product.models import Temper

                            temper_name = mapped["temper"]
                            temper_code = mapped.get("temper_code")
                            filter_kwargs = {"name__iexact": temper_name}
                            if temper_code:
                                filter_kwargs["code__iexact"] = temper_code
                            temper_instance = Temper.objects.filter(
                                **filter_kwargs
                            ).first()
                            if not temper_instance:
                                reason = f"Temper '{temper_name}'"
                                if temper_code:
                                    reason += f" with code '{temper_code}'"
                                reason += " not found"
                                result["skipped"] += 1
                                result["skipped_rows"].append(
                                    {"row_number": idx, "reason": reason}
                                )
                                continue
                            mapped["temper"] = temper_instance
                        except Exception as e:
                            result["skipped"] += 1
                            result["skipped_rows"].append(
                                {
                                    "row_number": idx,
                                    "reason": f"Error resolving temper: {str(e)}",
                                }
                            )
                            continue

                    # Remove helper fields before creating record
                    create_data = {
                        k: v
                        for k, v in mapped.items()
                        if k not in ["standard_name", "temper_code"]
                    }

                    self.model_class.objects.create(
                        **create_data, created_by=user, updated_by=user
                    )
                    result["inserted"] += 1
                    result["inserted_rows"].append({"row_number": idx})

            except Exception as e:
                result["skipped"] += 1
                result["skipped_rows"].append({"row_number": idx, "reason": str(e)})

        message_parts = []
        if result["inserted"]:
            message_parts.append(f"{result['inserted']} records inserted successfully")
        if result["updated"]:
            message_parts.append(f"{result['updated']} records updated successfully")
        if result["skipped"]:
            message_parts.append(f"{result['skipped']} record(s) skipped")
            # Add first skip reason to main message for quick debugging
            if result["skipped_rows"]:
                first_skip = result["skipped_rows"][0]
                if "reason" in first_skip:
                    message_parts.append(f"First skip reason: {first_skip['reason']}")

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

        if result["skipped_rows"]:
            response["skipped_details"] = result["skipped_rows"][:20]

        return response
