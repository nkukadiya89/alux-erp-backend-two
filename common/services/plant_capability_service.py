"""
Plant Capability Service
Provides helper functions for capability-driven business logic enforcement
"""

import logging
from typing import List, Optional, Tuple

from django.db.models import Q
from django.utils import timezone

from common.models import Plant, PlantCapability, PlantType, PlantTypeCapability

logger = logging.getLogger("file")


def has_capability(plant: Plant, capability_code: str) -> bool:
    """
    Check if a plant has a specific capability.

    Args:
        plant: Plant instance
        capability_code: Uppercase capability code (e.g., "PRODUCTION", "INVENTORY")

    Returns:
        bool: True if plant has the capability, False otherwise

    Example:
        if has_capability(plant, "PRODUCTION"):
            # Allow production order creation
    """
    if not plant or not plant.plant_type:
        return False

    if plant.status != "Active" or plant.deleted:
        return False

    capability_code = capability_code.upper().strip()

    try:
        mapping = (
            PlantTypeCapability.objects.filter(
                plant_type=plant.plant_type,
                capability__code=capability_code,
                status="Active",
                is_deleted=False,
            )
            .select_related("capability")
            .first()
        )

        if mapping:
            capability = mapping.capability
            if capability.status == "Active" and not capability.is_deleted:
                return True

        return False
    except Exception as e:
        logger.error(
            f"Error checking capability {capability_code} for plant {plant.id}: {str(e)}"
        )
        return False


def get_plant_capabilities(plant: Plant) -> List[str]:
    """
    Get all active capability codes for a plant.

    Args:
        plant: Plant instance

    Returns:
        List[str]: List of capability codes (e.g., ["PRODUCTION", "INVENTORY"])
    """
    if not plant or not plant.plant_type:
        return []

    if plant.status != "Active" or plant.deleted:
        return []

    try:
        mappings = (
            PlantTypeCapability.objects.filter(
                plant_type=plant.plant_type,
                status="Active",
                is_deleted=False,
                capability__status="Active",
                capability__is_deleted=False,
            )
            .select_related("capability")
            .values_list("capability__code", flat=True)
        )

        return list(mappings)
    except Exception as e:
        logger.error(f"Error getting capabilities for plant {plant.id}: {str(e)}")
        return []


def get_plants_with_capability(
    capability_code: str, active_only: bool = True
) -> List[Plant]:
    """
    Get all plants that have a specific capability.

    Args:
        capability_code: Uppercase capability code
        active_only: If True, return only active plants

    Returns:
        List[Plant]: List of Plant instances
    """
    capability_code = capability_code.upper().strip()

    try:
        capability = PlantCapability.objects.filter(
            code=capability_code, status="Active", is_deleted=False
        ).first()

        if not capability:
            return []

        query = Q(
            plant_type__capabilities__capability=capability,
            plant_type__capabilities__status="Active",
            plant_type__capabilities__is_deleted=False,
        )

        if active_only:
            query &= Q(status="Active", deleted=False)

        plants = Plant.objects.filter(query).distinct().select_related("plant_type")
        return list(plants)
    except Exception as e:
        logger.error(
            f"Error getting plants with capability {capability_code}: {str(e)}"
        )
        return []


def can_assign_capability(
    plant_type: PlantType, capability: PlantCapability
) -> Tuple[bool, Optional[str]]:
    """
    Check if a capability can be assigned to a plant type.

    Args:
        plant_type: PlantType instance
        capability: PlantCapability instance

    Returns:
        Tuple[bool, Optional[str]]: (can_assign, error_message)
    """
    if not plant_type or plant_type.is_deleted:
        return False, "Plant type is deleted or invalid"

    if not capability or capability.is_deleted:
        return False, "Capability is deleted or invalid"

    if capability.status != "Active":
        return False, "Capability is not active"

    # Check if mapping already exists
    existing = PlantTypeCapability.objects.filter(
        plant_type=plant_type, capability=capability, is_deleted=False
    ).exists()

    if existing:
        return False, "Capability is already assigned to this plant type"

    return True, None


def can_deactivate_capability_mapping(
    mapping: PlantTypeCapability,
) -> Tuple[bool, Optional[str]]:
    """
    Check if a capability mapping can be deactivated.

    Args:
        mapping: PlantTypeCapability instance

    Returns:
        Tuple[bool, Optional[str]]: (can_deactivate, error_message)
    """
    if not mapping:
        return False, "Mapping not found"

    # Check if active plants exist with this plant type
    active_plants = Plant.objects.filter(
        plant_type=mapping.plant_type, status="Active", deleted=False
    ).exists()

    if active_plants:
        return (
            False,
            "Cannot deactivate capability mapping. Active plants exist with this plant type.",
        )

    return True, None


def can_delete_capability(capability: PlantCapability) -> Tuple[bool, Optional[str]]:
    """
    Check if a capability can be deleted.

    Args:
        capability: PlantCapability instance

    Returns:
        Tuple[bool, Optional[str]]: (can_delete, error_message)
    """
    if not capability:
        return False, "Capability not found"

    # Check if capability is mapped to any plant type
    active_mappings = PlantTypeCapability.objects.filter(
        capability=capability, is_deleted=False
    ).exists()

    if active_mappings:
        return (
            False,
            "Cannot delete capability. It is mapped to one or more plant types.",
        )

    return True, None


def can_delete_plant_type(plant_type: PlantType) -> Tuple[bool, Optional[str]]:
    """
    Check if a PlantType can be deleted.

    Args:
        plant_type: PlantType instance

    Returns:
        Tuple[bool, Optional[str]]: (can_delete, error_message)
    """
    if not plant_type:
        return False, "Plant type not found"

    # Check if plant type is assigned to any plants
    active_plants = Plant.objects.filter(plant_type=plant_type, deleted=False).exists()

    if active_plants:
        return (
            False,
            "Cannot delete plant type. It is currently assigned to active plants.",
        )

    # Check if plant type has active capability mappings
    active_mappings = PlantTypeCapability.objects.filter(
        plant_type=plant_type, is_deleted=False
    ).exists()

    if active_mappings:
        return False, "Cannot delete plant type. It has active capability mappings."

    if plant_type.status == "Active":
        return False, "Cannot delete plant type. Plant type is currently active."

    return True, None


def create_plant_type_capability_mapping(
    plant_type_id: str,
    capability_id: str,
    user,
) -> Tuple[Optional[PlantTypeCapability], Optional[str]]:
    """
    Create a new plant type capability mapping.

    Args:
        plant_type_id: UUID of PlantType
        capability_id: UUID of PlantCapability
        user: User instance creating the mapping

    Returns:
        Tuple[Optional[PlantTypeCapability], Optional[str]]: (mapping, error_message)
    """
    try:
        plant_type = PlantType.objects.get(id=plant_type_id, is_deleted=False)
        capability = PlantCapability.objects.get(id=capability_id, is_deleted=False)
    except PlantType.DoesNotExist:
        return None, "Plant type not found."
    except PlantCapability.DoesNotExist:
        return None, "Capability not found."

    can_assign, error_message = can_assign_capability(plant_type, capability)
    if not can_assign:
        return None, error_message

    mapping = PlantTypeCapability.objects.create(
        plant_type=plant_type,
        capability=capability,
        status="Active",
        created_by=user,
        created_at=timezone.now(),
    )

    return mapping, None


def validate_plant_type_capability_update(
    mapping: PlantTypeCapability,
    new_status: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a plant type capability mapping can be updated.

    Args:
        mapping: PlantTypeCapability instance
        new_status: New status to validate (optional)

    Returns:
        Tuple[bool, Optional[str]]: (can_update, error_message)
    """
    if new_status == "Inactive":
        can_deactivate, error_message = can_deactivate_capability_mapping(mapping)
        if not can_deactivate:
            return False, error_message

    return True, None


def delete_plant_type_capability_mapping(
    mapping: PlantTypeCapability,
    user=None,
) -> Tuple[bool, Optional[str]]:
    """
    Soft delete a plant type capability mapping.

    Args:
        mapping: PlantTypeCapability instance
        user: User instance deleting the mapping

    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    can_deactivate, error_message = can_deactivate_capability_mapping(mapping)
    if not can_deactivate:
        return False, error_message

    mapping.is_deleted = True
    if user:
        mapping.updated_by = user
        mapping.updated_at = timezone.now()
    mapping.save()

    return True, None
