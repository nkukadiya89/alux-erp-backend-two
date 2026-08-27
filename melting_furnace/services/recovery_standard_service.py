"""
Recovery Standard Service
Business logic for Recovery Standard operations
"""

from typing import Tuple

from melting_furnace.models import RecoveryStandard


def can_deactivate_recovery_standard(instance: RecoveryStandard) -> Tuple[bool, str]:
    """
    Check if a recovery standard can be deactivated.

    Args:
        instance: RecoveryStandard instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    return True, None  # type: ignore


def can_archive_recovery_standard(instance: RecoveryStandard) -> Tuple[bool, str]:
    """
    Check if a recovery standard can be archived.

    Args:
        instance: RecoveryStandard instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if instance.deleted:
        return False, "Recovery Standard is already archived."

    if instance.status == "Active":
        return (
            False,
            "Cannot archive active recovery standard. Please deactivate it first.",
        )

    return True, None  # type: ignore


def can_delete_recovery_standard(instance: RecoveryStandard) -> Tuple[bool, str]:
    """
    Check if a recovery standard can be deleted.

    Args:
        instance: RecoveryStandard instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
