"""
Business rule validators for domain-specific validation
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from imports.validators.base import BaseValidator

logger = logging.getLogger(__name__)


class CustomBusinessRuleValidator(BaseValidator):
    """
    Validates business rules using custom validation function
    """

    def __init__(
        self,
        field_name: str,
        validation_func: Callable,
        error_message: str = None,
        required: bool = False,
    ):
        super().__init__(field_name, required)
        self.validation_func = validation_func
        self.error_message = error_message or f"{field_name} validation failed"

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        try:
            result = self.validation_func(value, row_data)

            if isinstance(result, tuple):
                return result  # (is_valid, error_message)
            elif isinstance(result, bool):
                return result, None if result else self.error_message
            else:
                return True, None

        except Exception as e:
            logger.error(
                f"Error in business rule validation for {self.field_name}: {str(e)}"
            )
            return False, f"Validation error: {str(e)}"


class ConditionalValidator(BaseValidator):
    """
    Validates field based on condition of another field
    """

    def __init__(
        self,
        field_name: str,
        condition_field: str,
        condition_func: Callable,
        validator: BaseValidator,
        required: bool = False,
    ):
        super().__init__(field_name, required)
        self.condition_field = condition_field
        self.condition_func = condition_func
        self.validator = validator

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        if row_data is None:
            return True, None

        # Check condition
        condition_value = row_data.get(self.condition_field)
        if not self.condition_func(condition_value):
            return True, None  # Condition not met, skip validation

        # Run validator if condition is met
        return self.validator.validate(value, row_data)


class CrossFieldValidator(BaseValidator):
    """
    Validates multiple fields together
    """

    def __init__(
        self, field_names: list, validation_func: Callable, error_message: str = None
    ):
        super().__init__("_".join(field_names), required=False)
        self.field_names = field_names
        self.validation_func = validation_func
        self.error_message = error_message or "Cross-field validation failed"

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        if row_data is None:
            return True, None

        try:
            # Extract all field values
            field_values = {field: row_data.get(field) for field in self.field_names}

            result = self.validation_func(field_values, row_data)

            if isinstance(result, tuple):
                return result
            elif isinstance(result, bool):
                return result, None if result else self.error_message
            else:
                return True, None

        except Exception as e:
            logger.error(f"Error in cross-field validation: {str(e)}")
            return False, f"Validation error: {str(e)}"
