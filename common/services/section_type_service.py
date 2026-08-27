"""
Section Type Master Service
Business logic for Section Type operations
"""

import logging
from typing import Tuple

from common.models import SectionType

logger = logging.getLogger("file")


def can_deactivate_section_type(section_type: SectionType) -> Tuple[bool, str]:
    """
    Check if a section type can be deactivated.

    Args:
        section_type: SectionType instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    # Future-safe: Check if section type is used in active transactions
    # For now, always allow deactivation
    # TODO: Add validation when department/section mapping is implemented
    # Example:
    # from common.models import Department
    # active_departments = Department.objects.filter(
    #     section_type=section_type,
    #     is_active=True,
    #     is_archived=False
    # ).exists()
    # if active_departments:
    #     return False, "Cannot deactivate section type. Active departments are using this section type."

    return True, None


def can_archive_section_type(section_type: SectionType) -> Tuple[bool, str]:
    """
    Check if a section type can be archived.

    Args:
        section_type: SectionType instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if section_type.is_archived:
        return False, "Section type is already archived."

    # Future-safe: Check if section type is used in active transactions
    # For now, always allow archiving
    # TODO: Add validation when department/section mapping is implemented
    # Example:
    # from common.models import Department
    # active_departments = Department.objects.filter(
    #     section_type=section_type,
    #     is_active=True,
    #     is_archived=False
    # ).exists()
    # if active_departments:
    #     return False, "Cannot archive section type. Active departments are using this section type."

    return True, None


def can_delete_section_type(section_type: SectionType) -> Tuple[bool, str]:
    """
    Check if a section type can be deleted (hard delete prevention).

    Args:
        section_type: SectionType instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    # Hard delete is not allowed - always return False
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
