"""
Department Master Service
Business logic for Department operations
"""

import logging
from typing import Tuple

from common.models import Department

logger = logging.getLogger("file")


def can_deactivate_department(department: Department) -> Tuple[bool, str]:
    """
    Check if a department can be deactivated.

    Args:
        department: Department instance to check

    Returns:
        Tuple of (can_deactivate, error_message)
    """
    # Future-safe: Check if department is used in active transactions
    # For now, always allow deactivation
    # TODO: Add validation when department is used in:
    # - Active employees
    # - Active work orders
    # - Active production orders
    # Example:
    # from user.models import Employee
    # active_employees = Employee.objects.filter(
    #     department=department,
    #     is_active=True,
    #     is_archived=False
    # ).exists()
    # if active_employees:
    #     return False, "Cannot deactivate department. Active employees are assigned to this department."

    return True, None


def can_archive_department(department: Department) -> Tuple[bool, str]:
    """
    Check if a department can be archived.

    Args:
        department: Department instance to check

    Returns:
        Tuple of (can_archive, error_message)
    """
    if department.is_archived:
        return False, "Department is already archived."

    # Cannot archive active departments - must deactivate first
    if department.status == "Active":
        return (
            False,
            "Cannot archive active department. Please deactivate the department first.",
        )

    # Check if department has active child departments
    active_children = Department.objects.filter(
        parent_department=department, is_archived=False, status="Active"
    ).exists()
    if active_children:
        return False, "Cannot archive department. Active child departments exist."

    # Future-safe: Check if department is used in active transactions
    # TODO: Add validation when department is used in:
    # - Active employees
    # - Active work orders
    # - Active production orders

    return True, None


def can_delete_department(department: Department) -> Tuple[bool, str]:
    """
    Check if a department can be deleted (hard delete prevention).

    Args:
        department: Department instance to check

    Returns:
        Tuple of (can_delete, error_message)
    """
    # Hard delete is not allowed - always return False
    return False, "Hard delete is not allowed. Use archive (soft delete) instead."
