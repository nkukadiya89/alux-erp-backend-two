"""
Item Master Service
Business logic for Item operations
"""

import logging
from typing import Tuple

from product.models import Item

logger = logging.getLogger("file")


def can_deactivate_item(item: Item) -> Tuple[bool, str]:
    """
    Check if a item can be deactivated.

    Args:
        item: Item instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    # Future-safe: Check if item is used in active transactions
    # For now, always allow deactivation
    # TODO: Add validation when item is used in:
    # - Active employees
    # - Active work orders
    # - Active production orders
    # Example:
    # from user.models import Employee
    # active_employees = Employee.objects.filter(
    #     item=item,
    #     is_active=True,
    #     is_archived=False
    # ).exists()
    # if active_employees:
    #     return False, "Cannot deactivate item. Active employees are assigned to this item."

    return True, None


def can_archive_item(item: Item) -> Tuple[bool, str]:
    """
    Check if a item can be archived.

    Args:
        item: Item instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if item.deleted:
        return False, "Item is already archived."

    # Cannot archive active items - must deactivate first
    if item.status == "Active":
        return (
            False,
            "Cannot archive active item. Please deactivate the item first.",
        )

    # Future-safe: Check if item is used in active transactions
    # TODO: Add validation when item is used in:
    # - Active employees
    # - Active work orders
    # - Active production orders

    return True, None


def can_delete_item(item: Item) -> Tuple[bool, str]:
    """
    Check if a item can be deleted (hard delete prevention).

    Args:
        item: Item instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    # Hard delete is not allowed - always return False
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
