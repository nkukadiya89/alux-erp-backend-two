import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, IntegrityError
from rest_framework import serializers
from rest_framework.response import Response


def custom_exception(exception):
    logger = logging.getLogger("file_logger")
    logger.error(f"Error occurred: {exception}", exc_info=True)

    error_messages = {
        ValueError: "Invalid input",
        serializers.ValidationError: "Validation error",
        IntegrityError: "Database integrity error",
        DatabaseError: "Database error",
    }
    if isinstance(exception, DjangoValidationError):
        msg = getattr(exception, "message", None)
        if msg is None and getattr(exception, "messages", None):
            msg = exception.messages[0] if exception.messages else str(exception)
        elif msg is None:
            msg = str(exception)
        return Response({"success": False, "message": str(msg)}, status=400)
    if isinstance(exception, serializers.ValidationError):

        def flatten_errors(detail):
            if isinstance(detail, dict):
                messages = []
                for key, value in detail.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                messages.extend(flatten_errors(item))
                            else:
                                messages.append(str(item))
                    elif isinstance(value, dict):
                        messages.extend(flatten_errors(value))
                    else:
                        messages.append(str(value))
                return messages
            elif isinstance(detail, list):
                messages = []
                for item in detail:
                    if isinstance(item, dict):
                        messages.extend(flatten_errors(item))
                    else:
                        messages.append(str(item))
                return messages
            else:
                return [str(detail)]

        error_messages = flatten_errors(exception.detail)
        error_message = ", ".join(error_messages)
        error_message = (
            error_message.replace("ErrorDetail(string='", "")
            .replace("', code='unique')", "")
            .replace('ErrorDetail(string="', "")
            .replace("\", code='unique')", "")
            .capitalize()
        )
        return Response({"success": False, "message": error_message}, status=400)
    elif isinstance(exception, (DatabaseError, IntegrityError)):
        error_message = error_messages.get(
            type(exception), "A database error occurred. Please try again."
        )
        return Response({"success": False, "message": error_message}, status=500)
    else:
        error_message = error_messages.get(
            type(exception), f"An error occurred: {str(exception)}"
        )
        # 400 for known client errors, 500 for unexpected server errors
        status_code = 400 if isinstance(exception, ValueError) else 500
        return Response(
            {"success": False, "message": error_message}, status=status_code
        )


def custom_exception_unique(exception):
    logger = logging.getLogger("file_logger")
    logger.error(f"Error occurred: {exception}", exc_info=True)

    error_messages = {
        ValueError: "Invalid input",
        serializers.ValidationError: "Validation error",
        IntegrityError: "Database integrity error",
        DatabaseError: "Database error",
    }
    if isinstance(exception, serializers.ValidationError):
        if isinstance(exception.detail, dict):
            error_message = ", ".join([" ".join(v) for v in exception.detail.values()])  # type: ignore
            error_message = (
                error_message.replace("ErrorDetail(string='", "")
                .replace("', code='unique')", "")
                .capitalize()
            )
        elif isinstance(exception.detail, list):
            error_message = ", ".join([str(v) for v in exception.detail])
        else:
            error_message = "Validation error"
    else:
        # For debugging, show actual error message
        error_message = error_messages.get(
            type(exception), f"An error occurred: {str(exception)}"
        )
    return Response({"success": False, "message": error_message}, status=400)
