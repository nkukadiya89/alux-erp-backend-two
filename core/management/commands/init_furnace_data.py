import csv
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from melting_furnace.models import FuelType, Furnace, FurnaceType

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize master data for Furnace from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/furnace.csv",
            help="Path to CSV file (relative to project root)",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]

        # Construct the full path
        if not os.path.isabs(csv_file_path):
            csv_file_path = os.path.join(settings.BASE_DIR, csv_file_path)

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        # Always initialize dependencies first
        self._initialize_dependencies()

        # Check for missing dependencies after initialization
        missing_dependencies = self._check_missing_dependencies(csv_file_path)
        if missing_dependencies:
            self.stdout.write(
                self.style.WARNING(
                    f"Some dependencies might be missing: {missing_dependencies}\n"
                    "Continuing with available data..."
                )
            )

        self._process_furnaces(csv_file_path)

    def _initialize_dependencies(self):
        """Initialize all required dependency commands"""
        dependency_commands = [
            ("init_furnace_type_data", "Furnace Type data"),
            ("init_fuel_type_data", "Fuel Type data"),
        ]

        self.stdout.write(self.style.WARNING("Initializing dependencies..."))

        for command_name, description in dependency_commands:
            try:
                self.stdout.write(f"  - Initializing {description}...", ending="")
                call_command(command_name, verbosity=0)
                self.stdout.write(self.style.SUCCESS(" ✓"))
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f" ⚠ (may already exist or command not found)")
                )

    def _check_missing_dependencies(self, csv_file_path):
        """Check which required dependencies are missing from the database"""
        missing = {"furnace_types": [], "fuel_types": []}

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                # Collect unique values from CSV
                unique_furnace_types = set()
                unique_fuel_types = set()

                for row in reader:
                    furnace_type_name = row.get("furnace_type", "").strip()
                    fuel_type_name = row.get("fuel_type", "").strip()

                    if furnace_type_name:
                        unique_furnace_types.add(furnace_type_name)
                    if fuel_type_name:
                        unique_fuel_types.add(fuel_type_name)

                # Check for missing furnace types
                existing_furnace_types = set(
                    FurnaceType.objects.filter(
                        name__in=unique_furnace_types
                    ).values_list("name", flat=True)
                )
                missing["furnace_types"] = list(
                    unique_furnace_types - existing_furnace_types
                )

                # Check for missing fuel types
                existing_fuel_types = set(
                    FuelType.objects.filter(name__in=unique_fuel_types).values_list(
                        "name", flat=True
                    )
                )
                missing["fuel_types"] = list(unique_fuel_types - existing_fuel_types)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking dependencies: {e}"))

        return {k: v for k, v in missing.items() if v}

    def _process_furnaces(self, csv_file_path):
        """Process the CSV file and create Furnace records"""
        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                created_count = 0
                updated_count = 0
                error_count = 0

                # Try to get a default user for created_by field
                default_user = User.objects.filter(is_superuser=True).first()

                for row_num, row in enumerate(reader, start=1):
                    try:
                        # Extract required fields
                        furnace_code = row.get("furnace_code", "").strip()
                        furnace_name = row.get("furnace_name", "").strip()
                        furnace_capacity = row.get("furnace_capacity", "").strip()

                        if not all([furnace_code, furnace_name, furnace_capacity]):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Missing required fields (furnace_code, furnace_name, furnace_capacity)"
                                )
                            )
                            error_count += 1
                            continue

                        # Convert capacity to decimal
                        try:
                            furnace_capacity_val = Decimal(str(furnace_capacity))
                        except (ValueError, TypeError):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Invalid numeric value for furnace_capacity"
                                )
                            )
                            error_count += 1
                            continue

                        # Prepare furnace data
                        furnace_data = {
                            "furnace_code": furnace_code,
                            "furnace_name": furnace_name,
                            "furnace_capacity": furnace_capacity_val,
                            "created_by": default_user,
                        }

                        # Optional fields
                        optional_fields = {
                            "min_temperature": "min_temperature",
                            "max_temperature": "max_temperature",
                            "status": "status",
                            "remark": "remark",
                        }

                        for field_name, csv_key in optional_fields.items():
                            value = row.get(csv_key, "").strip()
                            if value:
                                if field_name in ["min_temperature", "max_temperature"]:
                                    try:
                                        furnace_data[field_name] = Decimal(str(value))
                                    except (ValueError, TypeError):
                                        pass  # Skip invalid decimal values
                                else:
                                    furnace_data[field_name] = value

                        # Set default status if not provided
                        if "status" not in furnace_data:
                            furnace_data["status"] = "Active"

                        # Handle foreign key relationships
                        foreign_keys_set = self._set_foreign_keys(furnace_data, row)

                        if not foreign_keys_set:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Skipping due to missing foreign key relationships"
                                )
                            )
                            error_count += 1
                            continue

                        # Create or update Furnace
                        furnace, created = Furnace.objects.get_or_create(
                            furnace_code=furnace_code, defaults=furnace_data
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Created Furnace: {furnace_code}")
                            )
                        else:
                            # Update existing furnace with new data
                            for key, value in furnace_data.items():
                                if key != "created_by":  # Don't overwrite created_by
                                    setattr(furnace, key, value)
                            furnace.updated_by = default_user
                            furnace.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Updated existing Furnace: {furnace_code}"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing furnace {row.get('furnace_code', 'unknown')}: {e}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nFurnace data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Updated: {updated_count} existing records\n"
                        f"Errors: {error_count} records failed"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def _set_foreign_keys(self, furnace_data, row):
        """Set foreign key relationships for Furnace"""
        foreign_keys_found = 0

        # Furnace Type
        furnace_type_name = row.get("furnace_type", "").strip()
        if furnace_type_name:
            try:
                furnace_type = FurnaceType.objects.get(name=furnace_type_name)
                furnace_data["furnace_type"] = furnace_type
                foreign_keys_found += 1
            except FurnaceType.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Furnace Type not found: {furnace_type_name}")
                )

        # Fuel Type
        fuel_type_name = row.get("fuel_type", "").strip()
        if fuel_type_name:
            try:
                fuel_type = FuelType.objects.get(name=fuel_type_name)
                furnace_data["fuel_type"] = fuel_type
                foreign_keys_found += 1
            except FuelType.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Fuel Type not found: {fuel_type_name}")
                )

        # Return True if both required foreign keys are found
        return foreign_keys_found == 2
