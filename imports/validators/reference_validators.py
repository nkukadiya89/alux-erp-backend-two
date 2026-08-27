"""
Reference validators for foreign keys and related objects
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from django.db import models

from imports.utils import normalize_string
from imports.validators.base import BaseValidator

logger = logging.getLogger(__name__)


class ForeignKeyValidator(BaseValidator):
    """
    Validates foreign key references
    """

    def __init__(
        self,
        field_name: str,
        model_class: models.Model,
        lookup_field: str = None,
        required: bool = False,
        case_sensitive: bool = True,
    ):
        super().__init__(field_name, required)
        self.model_class = model_class
        self.lookup_field = lookup_field or "id"
        self.case_sensitive = case_sensitive
        self._cache = {}  # Cache lookups for performance

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        # Check cache first
        cache_key = str(value)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Perform lookup
        try:
            lookup_value = value

            # Handle case-insensitive lookups
            if not self.case_sensitive and isinstance(value, str):
                lookup_value = value.strip().upper()
                # Use __iexact for case-insensitive lookup
                lookup_kwargs = {f"{self.lookup_field}__iexact": lookup_value}
            else:
                lookup_kwargs = {self.lookup_field: lookup_value}

            exists = self.model_class.objects.filter(**lookup_kwargs).exists()

            if exists:
                self._cache[cache_key] = (True, None)
                return True, None
            else:
                error_msg = f"{self.field_name} '{value}' does not exist"
                self._cache[cache_key] = (False, error_msg)
                return False, error_msg

        except Exception as e:
            logger.error(f"Error validating {self.field_name}: {str(e)}")
            error_msg = f"Error validating {self.field_name}: {str(e)}"
            self._cache[cache_key] = (False, error_msg)
            return False, error_msg


class CustomReferenceValidator(BaseValidator):
    """
    Validates references using a custom lookup function
    """

    def __init__(self, field_name: str, lookup_func: Callable, required: bool = False):
        super().__init__(field_name, required)
        self.lookup_func = lookup_func

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        try:
            exists = self.lookup_func(value)
            if exists:
                return True, None
            else:
                return False, f"{self.field_name} '{value}' does not exist"
        except Exception as e:
            logger.error(f"Error validating {self.field_name}: {str(e)}")
            return False, f"Error validating {self.field_name}: {str(e)}"


class DatabaseUniqueValidator(BaseValidator):
    """
    Validates uniqueness against database (checks if value already exists)
    """

    def __init__(
        self,
        field_name: str,
        model_class: models.Model,
        lookup_field: str = None,
        required: bool = False,
        case_sensitive: bool = True,
        exclude_id: Any = None,
    ):
        super().__init__(field_name, required)
        self.model_class = model_class
        self.lookup_field = lookup_field or field_name
        self.case_sensitive = case_sensitive
        self.exclude_id = exclude_id

    def validate(self, value: Any, row_data: Dict = None) -> Tuple[bool, Optional[str]]:
        is_valid, error = self.validate_required(value)
        if not is_valid:
            return False, error

        if not self.required and (value is None or value == ""):
            return True, None

        try:
            if not self.case_sensitive and isinstance(value, str):
                lookup_kwargs = {f"{self.lookup_field}__iexact": value.strip().upper()}
            else:
                lookup_kwargs = {self.lookup_field: value}

            queryset = self.model_class.objects.filter(**lookup_kwargs)

            # Exclude current record if updating
            if self.exclude_id:
                queryset = queryset.exclude(pk=self.exclude_id)

            if queryset.exists():
                return False, f"{self.field_name} '{value}' already exists in database"

            return True, None

        except Exception as e:
            logger.error(f"Error validating uniqueness for {self.field_name}: {str(e)}")
            return False, f"Error validating {self.field_name}: {str(e)}"
