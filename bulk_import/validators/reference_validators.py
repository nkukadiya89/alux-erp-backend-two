# bulk_import/validators/reference_validators.py
from typing import Any, Dict

from django.apps import apps

from .validation_error import ValidationError


class DuplicateValidator:
    """Check for duplicates and mark action"""

    def __init__(self, model, field: str):
        if isinstance(model, str):
            self.model = apps.get_model(model)
        else:
            self.model = model
        self.field = field
        self._cache = {}  # Cache for performance

    def validate(self, row: Dict[str, Any]):
        """Check for duplicates and set action"""
        field_value = row.get(self.field)

        if field_value:
            cache_key = f"{self.model._meta.label}:{self.field}:{field_value}"

            # Check cache first
            if cache_key in self._cache:
                exists = self._cache[cache_key]
            else:
                exists = self.model.objects.filter(**{self.field: field_value}).exists()
                self._cache[cache_key] = exists

            if exists:
                row["_action"] = "UPDATE"
                # Don't raise error for duplicates, just mark as update
            else:
                row["_action"] = "INSERT"
        else:
            row["_action"] = "INSERT"


class ForeignKeyValidator:
    """Validate foreign key references"""

    def __init__(self, fk_mappings: Dict[str, Dict[str, str]]):
        """
        fk_mappings = {
            'field_name': {
                'model': 'app.Model',
                'lookup_field': 'name'
            }
        }
        """
        self.fk_mappings = fk_mappings
        self._cache = {}

    def validate(self, row: Dict[str, Any]):
        """Validate foreign key references"""
        errors = {}

        for field_name, config in self.fk_mappings.items():
            field_value = row.get(field_name)

            if field_value:  # Only validate if value is provided
                model_class = apps.get_model(config["model"])
                lookup_field = config["lookup_field"]

                cache_key = f"{config['model']}:{lookup_field}:{field_value}"

                if cache_key in self._cache:
                    exists = self._cache[cache_key]
                else:
                    exists = model_class.objects.filter(
                        **{lookup_field: field_value}
                    ).exists()
                    self._cache[cache_key] = exists

                if not exists:
                    errors[field_name] = f"{field_value} not found in {config['model']}"

        if errors:
            raise ValidationError("Foreign key validation failed", field_errors=errors)
