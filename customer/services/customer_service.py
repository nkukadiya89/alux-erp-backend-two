"""
Customer service layer for business logic validation and operations.
This module contains all business logic that should not be in views or serializers.
"""

import logging

from django.db import IntegrityError
from django.utils import timezone

from customer.models import BankingDetails, ContactPerson, Customer

logger = logging.getLogger(__name__)


def can_archive_customer(customer: Customer) -> tuple[bool, str]:
    """
    Check if a customer can be archived.

    Args:
        customer: Customer instance to check

    Returns:
        tuple: (can_archive: bool, error_message: str)
    """
    # TODO: Add business rule checks
    # - Check if customer has active orders
    # - Check if customer has pending invoices
    # - Check if customer has active contracts

    if customer.deleted:
        return False, "Customer is already archived."

    # Placeholder for future business rule validation
    return True, ""


def can_deactivate_customer(customer: Customer) -> tuple[bool, str]:
    """
    Check if a customer can be deactivated.

    Args:
        customer: Customer instance to check

    Returns:
        tuple: (can_deactivate: bool, error_message: str)
    """
    # TODO: Add business rule checks
    # - Check if customer has active orders
    # - Check if customer has pending invoices

    return True, ""


def handle_business_type_validation(business_type: str, validated_data: dict) -> dict:
    """
    Handle business type specific field validation and nullification.

    Args:
        business_type: Business type ("INDIAN" or "OVERSEAS")
        validated_data: Dictionary of validated data to modify

    Returns:
        dict: Modified validated_data
    """
    if business_type == "INDIAN":
        validated_data["beneficiary_agent_code"] = None
        validated_data["import_export_code"] = None
    else:
        validated_data["gstin_number"] = None
        validated_data["gst_type"] = None
        validated_data["pan_number"] = None
        validated_data["udyam_no"] = None
        validated_data["applicable_gst"] = None

    return validated_data


def handle_company_type_validation(company_type: str, validated_data: dict) -> dict:
    """
    Handle company type specific field validation and nullification.

    Args:
        company_type: Company type ("customer", "vendor", "customer_vendor")
        validated_data: Dictionary of validated data to modify

    Returns:
        dict: Modified validated_data
    """
    if company_type == "vendor":
        validated_data["customer_section_no"] = None
        validated_data["customer_type"] = None
        validated_data["sales_executive"] = None
        validated_data["sales_executive_assistant"] = None
        validated_data["delivery_days"] = None

    return validated_data
