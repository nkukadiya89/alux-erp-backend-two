"""
Furnace Service
Business logic for Furnace operations
"""

from typing import Tuple

from melting_furnace.models import Furnace


def can_deactivate_furnace(furnace: Furnace) -> Tuple[bool, str]:
    """
    Check if a furnace can be deactivated.

    Args:
        furnace: Furnace instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    # Check if furnace is used in active operations (placeholder)
    # TODO: Add validation when furnace is used in active melts/batches

    return True, None  # type: ignore


def can_archive_furnace(furnace: Furnace) -> Tuple[bool, str]:
    """
    Check if a furnace can be archived.

    Args:
        furnace: Furnace instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if furnace.deleted:
        return False, "Furnace is already archived."

    # Cannot archive active furnaces - must deactivate first
    if furnace.status == "Active":
        return (
            False,
            "Cannot archive active furnace. Please deactivate the furnace first.",
        )

    # TODO: Check if furnace is used in active transactions

    return True, None  # type: ignore


def can_delete_furnace(furnace: Furnace) -> Tuple[bool, str]:
    """
    Check if a furnace can be deleted (hard delete prevention).

    Args:
        furnace: Furnace instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
