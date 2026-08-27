import csv
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from common.models import UOM
from melting_furnace.models import AdditiveCategory, AdditiveMaster

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize master data for AdditiveMaster from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/additive_master.csv",
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

        self._process_additive_master(csv_file_path)

    def _initialize_dependencies(self):
        """Initialize all required dependency commands"""
        dependency_commands = [
            ("init_additive_category_data", "Additive Category data"),
            ("init_uom_data", "UOM data"),
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
        missing = {"additive_categories": [], "uoms": []}

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                # Collect unique values from CSV
                unique_categories = set()
                unique_units = set()

                for row in reader:
                    category_name = row.get("category", "").strip()
                    unit_code = row.get("unit", "").strip()

                    if category_name:
                        unique_categories.add(category_name)
                    if unit_code:
                        unique_units.add(unit_code)

                # Check for missing additive categories
                existing_categories = set(
                    AdditiveCategory.objects.filter(
                        name__in=unique_categories
                    ).values_list("name", flat=True)
                )
                missing["additive_categories"] = list(
                    unique_categories - existing_categories
                )

                # Check for missing UOMs
                existing_units = set(
                    UOM.objects.filter(uom_code__in=unique_units).values_list(
                        "uom_code", flat=True
                    )
                )
                missing["uoms"] = list(unique_units - existing_units)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking dependencies: {e}"))

        return {k: v for k, v in missing.items() if v}

    def _process_additive_master(self, csv_file_path):
        """Process the CSV file and create AdditiveMaster records"""
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
                        additive_code = row.get("additive_code", "").strip()
                        additive_name = row.get("additive_name", "").strip()
                        status = row.get("status", "Active").strip()

                        if not all([additive_code, additive_name]):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Missing required fields (additive_code, additive_name)"
                                )
                            )
                            error_count += 1
                            continue

                        # Prepare additive master data
                        additive_data = {
                            "additive_code": additive_code,
                            "additive_name": additive_name,
                            "status": status,
                            "created_by": default_user,
                        }

                        # Optional decimal fields
                        decimal_fields = {
                            "standard_quantity": "standard_quantity",
                            "min_limit": "min_limit",
                            "max_limit": "max_limit",
                        }

                        for field_name, csv_key in decimal_fields.items():
                            value = row.get(csv_key, "").strip()
                            if value:
                                try:
                                    additive_data[field_name] = Decimal(str(value))
                                except (ValueError, TypeError):
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Row {row_num}: Invalid decimal value for {field_name}: {value}"
                                        )
                                    )

                        # Optional text fields
                        remarks = row.get("remarks", "").strip()
                        if remarks:
                            additive_data["remarks"] = remarks

                        # Handle foreign key relationships
                        self._set_foreign_keys(additive_data, row, row_num)

                        # Create or update AdditiveMaster
                        additive, created = AdditiveMaster.objects.get_or_create(
                            additive_code=additive_code, defaults=additive_data
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created AdditiveMaster: {additive_code}"
                                )
                            )
                        else:
                            # Update existing additive with new data
                            for key, value in additive_data.items():
                                if key != "created_by":  # Don't overwrite created_by
                                    setattr(additive, key, value)
                            additive.updated_by = default_user
                            additive.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Updated existing AdditiveMaster: {additive_code}"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing additive {row.get('additive_code', 'unknown')}: {e}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nAdditive Master data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Updated: {updated_count} existing records\n"
                        f"Errors: {error_count} records failed"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def _set_foreign_keys(self, additive_data, row, row_num):
        """Set foreign key relationships for AdditiveMaster"""
        # Additive Category
        category_name = row.get("category", "").strip()
        if category_name:
            try:
                category = AdditiveCategory.objects.get(name=category_name)
                additive_data["category"] = category
            except AdditiveCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Row {row_num}: Additive Category not found: {category_name}"
                    )
                )

        # UOM
        unit_code = row.get("unit", "").strip()
        if unit_code:
            try:
                unit = UOM.objects.get(uom_code=unit_code)
                additive_data["unit"] = unit
            except UOM.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Row {row_num}: UOM not found: {unit_code}")
                )
