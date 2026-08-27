from decimal import Decimal, InvalidOperation

import pandas as pd


def excel_decimal(value):
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
