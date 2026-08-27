"""
Base validator classes for bulk import
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """
    Abstract base class for all validators
    """

    def __init__(self, field_name: str, required: bool = False):
        self.field_name = field_name
        self.required = required

    @abstractmethod
    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        """
        Validate a value.

        Args:
            value: Value to validate
            row_data: Complete row data for context-dependent validation

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    def validate_required(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Check if required field is present.

        Args:
            value: Value to check

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.required:
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, f"{self.field_name} is required"
        return True, None


class CompositeValidator(BaseValidator):
    """
    Validator that combines multiple validators
    """

    def __init__(
        self, field_name: str, validators: List[BaseValidator], required: bool = False
    ):
        super().__init__(field_name, required)
        self.validators = validators

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        """Run all validators in sequence"""
        # Check required first
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        # If value is None/empty and not required, skip other validators
        if not self.required and (
            value is None or (isinstance(value, str) and not value.strip())
        ):
            return True, None

        # Run all validators
        for validator in self.validators:
            is_valid, error = validator.validate(value, row_data)
            if not is_valid:
                return False, error

        return True, None
