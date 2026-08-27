"""
Field-level validators for common data types
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

from imports.utils import normalize_email, normalize_phone, normalize_string
from imports.validators.base import BaseValidator


class StringValidator(BaseValidator):
    """Validates string fields"""

    def __init__(
        self,
        field_name: str,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
        required: bool = False,
        pattern: Optional[str] = None,
    ):
        super().__init__(field_name, required)
        self.max_length = max_length
        self.min_length = min_length
        self.pattern = pattern

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (
            value is None or (isinstance(value, str) and not value.strip())
        ):
            return True, None

        value_str = normalize_string(value)
        if value_str is None:
            return False, f"{self.field_name} must be a valid string"

        if self.min_length and len(value_str) < self.min_length:
            return (
                False,
                f"{self.field_name} must be at least {self.min_length} characters",
            )

        if self.max_length and len(value_str) > self.max_length:
            return (
                False,
                f"{self.field_name} must be at most {self.max_length} characters",
            )

        if self.pattern:
            if not re.match(self.pattern, value_str):
                return (
                    False,
                    f"{self.field_name} contains invalid characters. Only letters, numbers, and spaces are allowed.",
                )

        return True, None


class EmailValidator(BaseValidator):
    """Validates email addresses"""

    EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (
            value is None or (isinstance(value, str) and not value.strip())
        ):
            return True, None

        email = normalize_email(value)
        if email is None:
            return False, f"{self.field_name} must be a valid email address"

        if not re.match(self.EMAIL_PATTERN, email):
            return False, f"{self.field_name} is not a valid email address"

        return True, None


class PhoneValidator(BaseValidator):
    """Validates phone numbers"""

    def __init__(
        self,
        field_name: str,
        min_length: int = 10,
        max_length: int = 15,
        required: bool = False,
    ):
        super().__init__(field_name, required)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (
            value is None or (isinstance(value, str) and not value.strip())
        ):
            return True, None

        phone = normalize_phone(value)
        if phone is None:
            return False, f"{self.field_name} must be a valid phone number"

        if not phone.isdigit():
            return False, f"{self.field_name} must contain only digits"

        if len(phone) < self.min_length or len(phone) > self.max_length:
            return (
                False,
                f"{self.field_name} must be between {self.min_length} and {self.max_length} digits",
            )

        return True, None


class IntegerValidator(BaseValidator):
    """Validates integer fields"""

    def __init__(
        self,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = False,
    ):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        try:
            int_value = int(float(str(value)))

            if self.min_value is not None and int_value < self.min_value:
                return False, f"{self.field_name} must be at least {self.min_value}"

            if self.max_value is not None and int_value > self.max_value:
                return False, f"{self.field_name} must be at most {self.max_value}"

            return True, None
        except (ValueError, TypeError):
            return False, f"{self.field_name} must be a valid integer"


class DecimalValidator(BaseValidator):
    """Validates decimal fields"""

    def __init__(
        self,
        field_name: str,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        required: bool = False,
    ):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        try:
            decimal_value = Decimal(str(value))

            if self.min_value is not None and decimal_value < self.min_value:
                return False, f"{self.field_name} must be at least {self.min_value}"

            if self.max_value is not None and decimal_value > self.max_value:
                return False, f"{self.field_name} must be at most {self.max_value}"

            # Check precision
            if self.max_digits or self.decimal_places:
                parts = str(decimal_value).split(".")
                integer_part = parts[0].lstrip("-")
                decimal_part = parts[1] if len(parts) > 1 else ""

                total_digits = len(integer_part) + len(decimal_part)
                if self.max_digits and total_digits > self.max_digits:
                    return (
                        False,
                        f"{self.field_name} exceeds maximum digits ({self.max_digits})",
                    )

                if self.decimal_places and len(decimal_part) > self.decimal_places:
                    return (
                        False,
                        f"{self.field_name} exceeds decimal places ({self.decimal_places})",
                    )

            return True, None
        except (InvalidOperation, ValueError, TypeError):
            return False, f"{self.field_name} must be a valid decimal number"


class ChoiceValidator(BaseValidator):
    """Validates choice fields"""

    def __init__(self, field_name: str, choices: list, required: bool = False):
        super().__init__(field_name, required)
        self.choices = choices  # List of (value, label) tuples or list of values

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (
            value is None or (isinstance(value, str) and not value.strip())
        ):
            return True, None

        value_str = normalize_string(value)
        if value_str is None:
            return False, f"{self.field_name} must be a valid choice"

        # Extract choice values
        choice_values = []
        for choice in self.choices:
            if isinstance(choice, tuple):
                choice_values.append(choice[0])
            else:
                choice_values.append(choice)

        # Check if value matches (case-insensitive)
        value_lower = value_str.lower()
        for choice_val in choice_values:
            if value_lower == str(choice_val).lower():
                return True, None

        valid_choices = ", ".join(
            [str(c[0] if isinstance(c, tuple) else c) for c in self.choices]
        )
        return False, f"{self.field_name} must be one of: {valid_choices}"


class UniqueValidator(BaseValidator):
    """Validates uniqueness (used for checking duplicates in import file)"""

    def __init__(self, field_name: str, seen_values: set, required: bool = False):
        super().__init__(field_name, required)
        self.seen_values = seen_values

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (
            value is None or (isinstance(value, str) and not value.strip())
        ):
            return True, None

        value_str = str(value).strip().upper() if isinstance(value, str) else str(value)

        if value_str in self.seen_values:
            return (
                False,
                f"{self.field_name} '{value}' is duplicated in the import file",
            )

        self.seen_values.add(value_str)
        return True, None
