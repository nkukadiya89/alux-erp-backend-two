"""
Item Category Master Service
Business logic for Item Category operations
"""

import logging
from typing import Tuple

from common.models import ItemCategory

logger = logging.getLogger("file")


def can_deactivate_item_category(item_category: ItemCategory) -> Tuple[bool, str]:
    """
    Check if an item category can be deactivated.

    Args:
        item_category: ItemCategory instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    # Future-safe: Check if category is used in active items
    # For now, always allow deactivation
    # TODO: Add validation when Item Master is implemented
    # Example:
    # from item.models import Item
    # active_items = Item.objects.filter(
    #     category=item_category,
    #     is_active=True,
    #     is_archived=False
    # ).exists()
    # if active_items:
    #     return False, "Cannot deactivate category. Active items are using this category."

    return True, None


def can_archive_item_category(item_category: ItemCategory) -> Tuple[bool, str]:
    """
    Check if an item category can be archived.

    Args:
        item_category: ItemCategory instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if item_category.is_archived:
        return False, "Item category is already archived."

    if item_category.status == "Active":
        return (
            False,
            "Cannot archive active category. Please deactivate the category first.",
        )

    # Future-safe: Check if category is used in active items
    # TODO: Add validation when Item Master is implemented
    # Example:
    # from item.models import Item
    # active_items = Item.objects.filter(
    #     category=item_category,
    #     is_active=True,
    #     is_archived=False
    # ).exists()
    # if active_items:
    #     return False, "Cannot archive category. Active items are using this category."

    return True, None


def can_delete_item_category(item_category: ItemCategory) -> Tuple[bool, str]:
    """
    Check if an item category can be deleted (hard delete prevention).

    Args:
        item_category: ItemCategory instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    # Hard delete is not allowed - always return False
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
