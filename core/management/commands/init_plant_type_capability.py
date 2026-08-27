import csv
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from common.models import PlantCapability, PlantType, PlantTypeCapability


class Command(BaseCommand):
    help = (
        "Initialize master data for PlantTypeCapability from CSV file with dependencies"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/plant_type_capability.csv",
            help="Path to CSV file (relative to project root)",
        )

    def handle(self, *args, **options):
        # Always initialize dependencies first
        self.init_dependencies()

        csv_file_path = options["csv_file"]

        # Construct the full path
        if not os.path.isabs(csv_file_path):
            csv_file_path = os.path.join(settings.BASE_DIR, csv_file_path)

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                created_count = 0
                existing_count = 0
                error_count = 0

                for row_num, row in enumerate(
                    reader, start=2
                ):  # Start from 2 to account for header
                    plant_type_code = row.get("plant_type", "").strip().upper()
                    capability_code = row.get("capability", "").strip().upper()

                    if not plant_type_code or not capability_code:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {row_num}: Skipping row with empty plant_type_code or capability_code"
                            )
                        )
                        continue

                    try:
                        # Look up PlantType
                        try:
                            plant_type = PlantType.objects.filter(
                                code=plant_type_code, is_deleted=False
                            ).first()
                            if not plant_type:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"Row {row_num}: PlantType '{plant_type_code}' not found"
                                    )
                                )
                                error_count += 1
                                continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Row {row_num}: Error looking up PlantType '{plant_type_code}': {str(e)}"
                                )
                            )
                            error_count += 1
                            continue

                        # Look up PlantCapability
                        try:
                            capability = PlantCapability.objects.filter(
                                code=capability_code, is_deleted=False
                            ).first()
                            if not capability:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"Row {row_num}: PlantCapability '{capability_code}' not found"
                                    )
                                )
                                error_count += 1
                                continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Row {row_num}: Error looking up PlantCapability '{capability_code}': {str(e)}"
                                )
                            )
                            error_count += 1
                            continue

                        # Get status (default to Active)
                        status = row.get("status", "Active").strip()
                        if status not in ["Active", "Inactive"]:
                            status = "Active"

                        # Create or get existing plant type capability mapping
                        obj, created = PlantTypeCapability.objects.get_or_create(
                            plant_type=plant_type,
                            capability=capability,
                            defaults={"status": status, "is_deleted": False},
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created PlantTypeCapability: {plant_type_code} -> {capability_code}"
                                )
                            )
                        else:
                            # Update existing record if needed
                            updated = False
                            if obj.status != status:
                                obj.status = status
                                updated = True
                            if obj.is_deleted:
                                obj.is_deleted = False
                                updated = True

                            if updated:
                                obj.save()
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"Updated PlantTypeCapability: {plant_type_code} -> {capability_code}"
                                    )
                                )
                            else:
                                existing_count += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"PlantTypeCapability already exists: {plant_type_code} -> {capability_code}"
                                    )
                                )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing mapping {plant_type_code} -> {capability_code}: {str(e)}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nPlant Type Capability mapping initialization complete!\n"
                        f"Created: {created_count} new mappings\n"
                        f"Existing: {existing_count} mappings already present\n"
                        f"Errors: {error_count} mappings failed"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def init_dependencies(self):
        """Initialize foreign key dependencies"""
        self.stdout.write(
            self.style.SUCCESS("Initializing PlantTypeCapability dependencies...")
        )

        # Initialize PlantType
        self.stdout.write("Initializing PlantType...")
        try:
            call_command("init_plant_type_data")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"PlantType initialization failed: {str(e)}")
            )

        # Initialize PlantCapability
        self.stdout.write("Initializing PlantCapability...")
        try:
            call_command("init_plant_capability")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"PlantCapability initialization failed: {str(e)}")
            )
