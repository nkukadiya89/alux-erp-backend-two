# bulk_import/validators/business_rules.py
from decimal import Decimal
from typing import Any, Dict

from .validation_error import ValidationError


class CustomerBusinessRuleValidator:
    """Business rules specific to Customer model"""

    def validate(self, row: Dict[str, Any]):
        """Validate customer business rules"""
        errors = {}

        # Rule 1: If business_type is OVERSEAS, import_export_code should be provided
        if row.get("business_type") == "OVERSEAS" and not row.get("import_export_code"):
            errors["import_export_code"] = (
                "Import/Export code is required for overseas customers"
            )

        # Rule 2: Customer name should not contain special characters
        customer_name = row.get("customer_name")
        if customer_name:
            import re

            if re.search(r"[<>{}[\]\\]", customer_name):
                errors["customer_name"] = "Customer name contains invalid characters"

        # Rule 3: GSTIN format validation
        gstin = row.get("gstin_number")
        if gstin and not re.match(r"^[0-9A-Z]{15}$", gstin):
            errors["gstin_number"] = "GSTIN must be 15 alphanumeric characters"

        # Rule 4: PAN format validation
        pan = row.get("pan_number")
        if pan and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan):
            errors["pan_number"] = "Invalid PAN format (ABCDE1234F)"

        if errors:
            raise ValidationError(
                "Business rule validation failed", field_errors=errors
            )
