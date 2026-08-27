"""
Plant Service
Provides business logic for Plant operations
"""

import logging
from typing import Optional, Tuple

from common.models import Plant

logger = logging.getLogger("file")


def can_deactivate_plant(plant: Plant) -> Tuple[bool, Optional[str]]:
    """
    Check if a plant can be deactivated.

    Args:
        plant: Plant instance

    Returns:
        Tuple[bool, Optional[str]]: (can_deactivate, error_message)
    """
    if not plant:
        return False, "Plant not found"

    # Business rule: Cannot deactivate plant if:
    # - Inventory stock exists (to be implemented when inventory module is ready)
    # - Open Purchase Orders exist (to be implemented when procurement module is ready)
    # TODO: Add checks when inventory and procurement modules are available
    # from inventory.models import InventoryStock
    # from procurement.models import PurchaseOrder
    #
    # if InventoryStock.objects.filter(plant=plant, quantity__gt=0).exists():
    #     return False, "Plant has inventory stock"
    # if PurchaseOrder.objects.filter(plant=plant, status__in=['Open', 'Pending']).exists():
    #     return False, "Plant has open purchase orders"

    return True, None


def can_delete_plant(plant: Plant) -> Tuple[bool, Optional[str]]:
    """
    Check if a plant can be deleted.

    Args:
        plant: Plant instance

    Returns:
        Tuple[bool, Optional[str]]: (can_delete, error_message)
    """
    if not plant:
        return False, "Plant not found"

    # Business rule: Cannot delete plant if:
    # - Plant has inventory stock
    # - Plant has open purchase orders
    # - Plant is currently active
    if plant.status == "Active":
        return False, "Cannot delete active plant. Please deactivate it first."

    # TODO: Add checks when inventory and procurement modules are available
    # from inventory.models import InventoryStock
    # from procurement.models import PurchaseOrder
    #
    # if InventoryStock.objects.filter(plant=plant, quantity__gt=0).exists():
    #     return False, "Plant has inventory stock"
    # if PurchaseOrder.objects.filter(plant=plant, status__in=['Open', 'Pending']).exists():
    #     return False, "Plant has open purchase orders"

    return True, None
