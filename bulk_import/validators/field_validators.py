# bulk_import/validators/field_validators.py
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from .validation_error import ValidationError


class RequiredFieldValidator:
    """Validate required fields"""

    def __init__(self, fields: List[str]):
        self.fields = fields

    def validate(self, row: Dict[str, Any]):
        """Validate that required fields are present and not empty"""
        missing_fields = []

        for field in self.fields:
            if not row.get(field) or str(row[field]).strip() == "":
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(
                f"Required fields missing: {', '.join(missing_fields)}",
                field_errors={
                    field: "This field is required" for field in missing_fields
                },
            )


class EmailFieldValidator:
    """Validate email fields"""

    def __init__(self, email_fields: List[str]):
        self.email_fields = email_fields

    def validate(self, row: Dict[str, Any]):
        """Validate email format"""
        errors = {}

        for field in self.email_fields:
            email = row.get(field)
            if email:  # Only validate if email is provided
                try:
                    validate_email(email)
                except DjangoValidationError:
                    errors[field] = "Invalid email format"

        if errors:
            raise ValidationError("Email validation failed", field_errors=errors)


class PhoneFieldValidator:
    """Validate phone number fields"""

    def __init__(self, phone_fields: List[str]):
        self.phone_fields = phone_fields

    def validate(self, row: Dict[str, Any]):
        """Validate phone number format"""
        errors = {}

        for field in self.phone_fields:
            phone = row.get(field)
            if phone:  # Only validate if phone is provided
                # Remove all non-digits
                cleaned_phone = re.sub(r"\D", "", str(phone))

                # Check if it's a valid 10-digit Indian number
                if not re.match(r"^\d{10}$", cleaned_phone):
                    errors[field] = "Phone number must be 10 digits"
                else:
                    # Update the row with cleaned phone number
                    row[field] = cleaned_phone

        if errors:
            raise ValidationError("Phone validation failed", field_errors=errors)


class NumericFieldValidator:
    """Validate numeric fields"""

    def __init__(self, numeric_fields: List[str], allow_negative: bool = True):
        self.numeric_fields = numeric_fields
        self.allow_negative = allow_negative

    def validate(self, row: Dict[str, Any]):
        """Validate numeric format"""
        errors = {}

        for field in self.numeric_fields:
            value = row.get(field)
            if value is not None and value != "":  # Only validate if value is provided
                try:
                    numeric_value = Decimal(str(value))

                    if not self.allow_negative and numeric_value < 0:
                        errors[field] = "Negative values not allowed"
                    else:
                        # Update row with proper numeric value
                        row[field] = numeric_value

                except (InvalidOperation, ValueError):
                    errors[field] = "Invalid numeric format"

        if errors:
            raise ValidationError("Numeric validation failed", field_errors=errors)


class ChoiceFieldValidator:
    """Validate choice fields"""

    def __init__(self, choice_mappings: Dict[str, Dict[str, str]]):
        self.choice_mappings = choice_mappings

    def validate(self, row: Dict[str, Any]):
        """Validate choice field values"""
        errors = {}

        for field, choices in self.choice_mappings.items():
            value = row.get(field)
            if value:  # Only validate if value is provided
                value_upper = str(value).upper().strip()

                if value_upper not in choices:
                    valid_choices = list(choices.keys())
                    errors[field] = (
                        f"Invalid choice. Valid options: {', '.join(valid_choices)}"
                    )
                else:
                    # Update row with mapped value
                    row[field] = choices[value_upper]

        if errors:
            raise ValidationError("Choice validation failed", field_errors=errors)


class LengthFieldValidator:
    """Validate field length"""

    def __init__(self, length_constraints: Dict[str, Dict[str, int]]):
        """
        length_constraints = {
            'field_name': {'max_length': 100, 'min_length': 2}
        }
        """
        self.length_constraints = length_constraints

    def validate(self, row: Dict[str, Any]):
        """Validate field lengths"""
        errors = {}

        for field, constraints in self.length_constraints.items():
            value = row.get(field)
            if value:  # Only validate if value is provided
                value_str = str(value).strip()
                length = len(value_str)

                max_length = constraints.get("max_length")
                min_length = constraints.get("min_length")

                if max_length and length > max_length:
                    errors[field] = f"Maximum length is {max_length} characters"

                if min_length and length < min_length:
                    errors[field] = f"Minimum length is {min_length} characters"

        if errors:
            raise ValidationError("Length validation failed", field_errors=errors)
