"""
Utility functions for bulk import module
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def excel_decimal(value: Any) -> Optional[Decimal]:
    """
    Convert Excel value to Decimal for database storage.
    Handles various Excel data types and returns None for empty/invalid values.

    Args:
        value: Value from Excel cell (could be float, string, int, etc.)

    Returns:
        Decimal or None
    """
    if pd.isna(value) or value == "" or value is None:
        return None

    try:
        if isinstance(value, float):
            value_str = str(value)
            if "e" in value_str.lower() or "." in value_str:
                return Decimal(str(value))
            else:
                return Decimal(value)
        else:
            return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_string(value: Any) -> Optional[str]:
    """
    Normalize string values from Excel/CSV.
    Converts numeric values like 24281.0 -> 24281
    """

    if pd.isna(value) or value is None:
        return None

    # Excel float: 24281.0 -> "24281"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()

    # Excel int
    if isinstance(value, int):
        return str(value)

    value_str = str(value).strip()

    # String "24281.0" -> "24281"
    try:
        f = float(value_str)
        if f.is_integer():
            return str(int(f))
    except (ValueError, TypeError):
        pass

    return value_str if value_str else None


def normalize_boolean(value: Any) -> Optional[bool]:
    """
    Normalize boolean values from Excel/CSV.
    Handles various boolean representations.

    Args:
        value: Value from Excel/CSV cell

    Returns:
        bool or None
    """
    if pd.isna(value) or value is None or value == "":
        return None

    if isinstance(value, bool):
        return value

    value_str = str(value).strip().lower()
    if value_str in ("true", "1", "yes", "y", "on"):
        return True
    elif value_str in ("false", "0", "no", "n", "off"):
        return False

    return None


def normalize_integer(value: Any) -> Optional[int]:
    """
    Normalize integer values from Excel/CSV.

    Args:
        value: Value from Excel/CSV cell

    Returns:
        int or None
    """
    if pd.isna(value) or value is None or value == "":
        return None

    try:
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


def normalize_email(value: Any) -> Optional[str]:
    """
    Normalize and validate email addresses.

    Args:
        value: Value from Excel/CSV cell

    Returns:
        str or None
    """
    email = normalize_string(value)
    if email and "@" in email and "." in email.split("@")[-1]:
        return email.lower()
    return email if email else None


def normalize_phone(value: Any) -> Optional[str]:
    """
    Normalize phone numbers.
    Removes common formatting characters.

    Args:
        value: Value from Excel/CSV cell

    Returns:
        str or None
    """
    phone = normalize_string(value)
    if phone:
        # Remove common formatting
        phone = (
            phone.replace("-", "")
            .replace(" ", "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
        )
        return phone if phone else None
    return None


def normalize_choice(value: Any, choices: List[tuple]) -> Optional[str]:
    """
    Normalize choice field values.
    Matches case-insensitively against available choices.

    Args:
        value: Value from Excel/CSV cell
        choices: List of (value, label) tuples

    Returns:
        str or None (matched choice value)
    """
    if pd.isna(value) or value is None:
        return None

    value_str = str(value).strip()
    if not value_str:
        return None

    # Try exact match first
    for choice_value, choice_label in choices:
        if value_str == choice_value or value_str == choice_label:
            return choice_value

    # Try case-insensitive match
    value_lower = value_str.lower()
    for choice_value, choice_label in choices:
        if value_lower == choice_value.lower() or value_lower == choice_label.lower():
            return choice_value

    return None


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean DataFrame by:
    - Stripping column names
    - Removing completely empty rows
    - Trimming string values

    Args:
        df: Input DataFrame

    Returns:
        Cleaned DataFrame
    """
    # Strip column names
    df.columns = df.columns.str.strip()

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Reset index
    df = df.reset_index(drop=True)

    return df


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate file extension.

    Args:
        filename: File name
        allowed_extensions: List of allowed extensions (e.g., ['.xlsx', '.csv'])

    Returns:
        bool: True if valid
    """
    if not filename:
        return False

    file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    return file_ext in [ext.lower() for ext in allowed_extensions]


def get_file_type(filename: str) -> Optional[str]:
    """
    Determine file type from filename.

    Args:
        filename: File name

    Returns:
        'excel' or 'csv' or None
    """
    if not filename:
        return None

    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["xlsx", "xls"]:
        return "excel"
    elif ext == "csv":
        return "csv"
    return None


def chunk_list(lst: List, chunk_size: int):
    """
    Split list into chunks of specified size.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Yields:
        Chunks of the list
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]
