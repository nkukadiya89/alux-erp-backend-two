# bulk_import/validators/validation_error.py
class ValidationError(Exception):
    """Custom validation error"""

    def __init__(self, message: str, field_errors: dict | None = None):
        super().__init__(message)
        self.field_errors = field_errors or {}
