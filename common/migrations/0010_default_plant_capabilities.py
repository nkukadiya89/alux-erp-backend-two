# Data migration for default Plant Capabilities and Plant Type mappings

import uuid

from django.conf import settings
from django.db import migrations


def create_default_capabilities(apps, schema_editor):
    """
    Create default Plant Capabilities:
    - PRODUCTION
    - INVENTORY
    - DISPATCH
    - CONSUMPTION
    - FINANCE
    - PURCHASE
    - QUALITY
    """
    PlantCapability = apps.get_model("common", "PlantCapability")

    capabilities = [
        {
            "code": "PRODUCTION",
            "name": "Production",
            "description": "Can create and manage production orders",
            "status": "Active",
        },
        {
            "code": "INVENTORY",
            "name": "Inventory",
            "description": "Can manage inventory stock and movements",
            "status": "Active",
        },
        {
            "code": "DISPATCH",
            "name": "Dispatch",
            "description": "Can dispatch goods and manage shipments",
            "status": "Active",
        },
        {
            "code": "CONSUMPTION",
            "name": "Material Consumption",
            "description": "Can record material consumption",
            "status": "Active",
        },
        {
            "code": "FINANCE",
            "name": "Financial Transactions",
            "description": "Can process financial transactions",
            "status": "Active",
        },
        {
            "code": "PURCHASE",
            "name": "Purchase Management",
            "description": "Can create and manage purchase orders",
            "status": "Active",
        },
        {
            "code": "QUALITY",
            "name": "Quality Control",
            "description": "Can perform quality control operations",
            "status": "Active",
        },
    ]

    for cap_data in capabilities:
        PlantCapability.objects.get_or_create(
            code=cap_data["code"],
            defaults={
                "name": cap_data["name"],
                "description": cap_data["description"],
                "status": cap_data["status"],
                "is_deleted": False,
            },
        )


def create_default_mappings(apps, schema_editor):
    """
    Create default Plant Type ↔ Capability mappings
    """
    PlantType = apps.get_model("common", "PlantType")
    PlantCapability = apps.get_model("common", "PlantCapability")
    PlantTypeCapability = apps.get_model("common", "PlantTypeCapability")

    # Default mappings: which capabilities each plant type should have
    DEFAULT_MAPPINGS = {
        "EXTRUSION": ["PRODUCTION", "INVENTORY", "CONSUMPTION", "QUALITY"],
        "FABRICATION": ["PRODUCTION", "INVENTORY", "CONSUMPTION", "QUALITY"],
        "WAREHOUSE": ["INVENTORY", "DISPATCH"],
        "SITE": ["INVENTORY", "DISPATCH"],
        "OFFICE": ["FINANCE", "PURCHASE"],
        "MELTING_CASTING": ["PRODUCTION", "INVENTORY", "CONSUMPTION", "QUALITY"],
        "HEAT_TREATMENT": ["PRODUCTION", "INVENTORY", "CONSUMPTION", "QUALITY"],
        "ANODIZING": ["PRODUCTION", "INVENTORY", "CONSUMPTION", "QUALITY"],
        "POWDER_COATING": ["PRODUCTION", "INVENTORY", "CONSUMPTION", "QUALITY"],
        "QUALITY_LAB": ["QUALITY"],
    }

    for plant_type_code, capability_codes in DEFAULT_MAPPINGS.items():
        try:
            plant_type = PlantType.objects.get(code=plant_type_code, is_deleted=False)
        except PlantType.DoesNotExist:
            continue  # Skip if plant type doesn't exist

        for cap_code in capability_codes:
            try:
                capability = PlantCapability.objects.get(
                    code=cap_code, is_deleted=False
                )
            except PlantCapability.DoesNotExist:
                continue  # Skip if capability doesn't exist

            # Create mapping if it doesn't exist
            PlantTypeCapability.objects.get_or_create(
                plant_type=plant_type,
                capability=capability,
                defaults={
                    "status": "Active",
                    "is_deleted": False,
                },
            )


def reverse_defaults(apps, schema_editor):
    """
    Reverse: Remove default capabilities and mappings
    Note: This will only remove if they match exactly
    """
    PlantCapability = apps.get_model("common", "PlantCapability")
    PlantTypeCapability = apps.get_model("common", "PlantTypeCapability")

    # Remove mappings
    PlantTypeCapability.objects.filter(is_deleted=False).delete()

    # Remove capabilities (optional - comment out if you want to keep them)
    # default_codes = ['PRODUCTION', 'INVENTORY', 'DISPATCH', 'CONSUMPTION', 'FINANCE', 'PURCHASE', 'QUALITY']
    # PlantCapability.objects.filter(code__in=default_codes, is_deleted=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0009_migrate_plant_to_plant_type_fk"),
    ]

    operations = [
        migrations.RunPython(
            create_default_capabilities,
            reverse_code=reverse_defaults,
        ),
        migrations.RunPython(
            create_default_mappings,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
