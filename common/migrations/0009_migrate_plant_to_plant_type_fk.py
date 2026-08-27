# Migration to convert Plant.plant_type from CharField to FK

import django.db.models.deletion
from django.db import migrations, models


def migrate_plant_types_forward(apps, schema_editor):
    """
    Create PlantType records from existing plant_type CharField values
    and migrate Plant.plant_type from CharField to FK
    """
    Plant = apps.get_model("common", "Plant")
    PlantType = apps.get_model("common", "PlantType")

    # Mapping of old CharField values to new PlantType codes
    # Based on original choices from migration 0006
    PLANT_TYPE_MAPPING = {
        "Extrusion": ("EXTRUSION", "Extrusion Plant"),
        "Assembly": ("FABRICATION", "Fabrication / Assembly Plant"),
        "Warehouse": ("WAREHOUSE", "Warehouse / Dispatch Center"),
        "Site": ("SITE", "Project / Site"),
        "Office": ("OFFICE", "Corporate Office"),
        # Also handle any other values that might exist
        "MELTING_CASTING": ("MELTING_CASTING", "Melting / Casting Plant"),
        "EXTRUSION": ("EXTRUSION", "Extrusion Plant"),
        "HEAT_TREATMENT": ("HEAT_TREATMENT", "Heat Treatment / Ageing Plant"),
        "ANODIZING": ("ANODIZING", "Anodizing Plant"),
        "POWDER_COATING": ("POWDER_COATING", "Powder Coating Plant"),
        "FABRICATION": ("FABRICATION", "Fabrication / Assembly Plant"),
        "WAREHOUSE": ("WAREHOUSE", "Warehouse / Dispatch Center"),
        "SITE": ("SITE", "Project / Site"),
        "QUALITY_LAB": ("QUALITY_LAB", "Quality Control / Testing Lab"),
        "OFFICE": ("OFFICE", "Corporate Office"),
    }

    # Create PlantType records
    plant_type_map = {}
    for old_code, (new_code, name) in PLANT_TYPE_MAPPING.items():
        plant_type, created = PlantType.objects.get_or_create(
            code=new_code,
            defaults={
                "name": name,
                "status": "Active",
                "is_deleted": False,
            },
        )
        plant_type_map[old_code] = plant_type

    # Get default plant type (OFFICE) for NULL/empty/invalid values
    default_plant_type = plant_type_map.get("OFFICE") or plant_type_map.get("Office")
    if not default_plant_type:
        default_plant_type, _ = PlantType.objects.get_or_create(
            code="OFFICE",
            defaults={
                "name": "Corporate Office",
                "status": "Active",
                "is_deleted": False,
            },
        )

    # Migrate Plant records
    for plant in Plant.objects.all():
        old_plant_type = plant.plant_type  # This is still CharField at this point

        # Handle NULL, empty, or invalid plant_type values
        if not old_plant_type or (
            isinstance(old_plant_type, str) and old_plant_type.strip() == ""
        ):
            # Use default plant type for NULL/empty values
            plant.plant_type_fk = default_plant_type
            plant.save()
        elif old_plant_type in plant_type_map:
            plant.plant_type_fk = plant_type_map[old_plant_type]
            plant.save()
        else:
            # If plant_type doesn't match any mapping, use default
            # Log this case for manual review
            print(
                f"Warning: Plant {getattr(plant, 'plant_code', 'Unknown')} has unknown plant_type '{old_plant_type}', assigning default OFFICE"
            )
            plant.plant_type_fk = default_plant_type
            plant.save()


def migrate_plant_types_backward(apps, schema_editor):
    """
    Reverse migration: convert FK back to CharField
    """
    Plant = apps.get_model("common", "Plant")

    for plant in Plant.objects.all():
        if hasattr(plant, "plant_type_fk") and plant.plant_type_fk:
            # Convert FK code back to CharField value
            plant_type_code = plant.plant_type_fk.code
            # Map back to original choice values
            code_mapping = {
                "EXTRUSION": "Extrusion",
                "FABRICATION": "Assembly",
                "WAREHOUSE": "Warehouse",
                "SITE": "Site",
                "OFFICE": "Office",
            }
            plant.plant_type = code_mapping.get(plant_type_code, "Office")
            plant.save()


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0008_plant_capability_architecture"),
    ]

    operations = [
        # Add temporary FK field (nullable)
        migrations.AddField(
            model_name="plant",
            name="plant_type_fk",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="plants_temp",
                to="common.planttype",
                db_index=True,
            ),
        ),
        # Migrate data from CharField to FK
        migrations.RunPython(migrate_plant_types_forward, migrate_plant_types_backward),
        # Remove old CharField
        migrations.RemoveField(
            model_name="plant",
            name="plant_type",
        ),
        # Rename FK field to plant_type
        migrations.RenameField(
            model_name="plant",
            old_name="plant_type_fk",
            new_name="plant_type",
        ),
        # Ensure all plants have a plant_type (safety check)
        migrations.RunSQL(
            sql="UPDATE plant SET plant_type_id = (SELECT id FROM plant_type WHERE code = 'OFFICE' LIMIT 1) WHERE plant_type_id IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Update related_name and make NOT NULL
        migrations.AlterField(
            model_name="plant",
            name="plant_type",
            field=models.ForeignKey(
                db_index=True,
                help_text="Plant type determines available capabilities",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="plants",
                to="common.planttype",
            ),
        ),
    ]
