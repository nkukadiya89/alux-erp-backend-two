"""
Additive Master Service
Business logic for Additive Master operations
"""

from typing import Tuple

from melting_furnace.models import AdditiveMaster


def can_deactivate_additive_master(instance: AdditiveMaster) -> Tuple[bool, str]:
    """
    Check if an additive master can be deactivated.

    Args:
        instance: AdditiveMaster instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    return True, None  # type: ignore


def can_archive_additive_master(instance: AdditiveMaster) -> Tuple[bool, str]:
    """
    Check if an additive master can be archived.

    Args:
        instance: AdditiveMaster instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if instance.deleted:
        return False, "Additive Master is already archived."

    if instance.status == "Active":
        return (
            False,
            "Cannot archive active additive master. Please deactivate it first.",
        )

    return True, None  # type: ignore


def can_delete_additive_master(instance: AdditiveMaster) -> Tuple[bool, str]:
    """
    Check if an additive master can be deleted.

    Args:
        instance: AdditiveMaster instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
