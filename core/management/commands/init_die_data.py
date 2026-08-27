import csv
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from die.models import Die, DieCategory, DieGroup, DieSubCategory

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize master data for Die from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/die_sample.csv",
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

        self._process_dies(csv_file_path)

    def _initialize_dependencies(self):
        """Initialize all required dependency commands"""
        dependency_commands = [
            ("init_die_group_data", "Die Group data"),
            ("init_die_category_data", "Die Category data"),
            ("init_die_sub_category_data", "Die Sub Category data"),
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
        missing = {"die_groups": [], "die_categories": [], "die_sub_categories": []}

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                # Collect unique values from CSV
                unique_groups = set()
                unique_categories = set()
                unique_sub_categories = set()

                for row in reader:
                    die_group_name = row.get("die_group", "").strip()
                    die_category_name = row.get("die_category", "").strip()
                    die_sub_category_name = row.get("die_sub_category", "").strip()

                    if die_group_name:
                        unique_groups.add(die_group_name)
                    if die_category_name:
                        unique_categories.add(die_category_name)
                    if die_sub_category_name:
                        unique_sub_categories.add(die_sub_category_name)

                # Check for missing die groups
                existing_groups = set(
                    DieGroup.objects.filter(name__in=unique_groups).values_list(
                        "name", flat=True
                    )
                )
                missing["die_groups"] = list(unique_groups - existing_groups)

                # Check for missing die categories
                existing_categories = set(
                    DieCategory.objects.filter(name__in=unique_categories).values_list(
                        "name", flat=True
                    )
                )
                missing["die_categories"] = list(
                    unique_categories - existing_categories
                )

                # Check for missing die sub categories
                existing_sub_categories = set(
                    DieSubCategory.objects.filter(
                        name__in=unique_sub_categories
                    ).values_list("name", flat=True)
                )
                missing["die_sub_categories"] = list(
                    unique_sub_categories - existing_sub_categories
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking dependencies: {e}"))

        return {k: v for k, v in missing.items() if v}

    def _process_dies(self, csv_file_path):
        """Process the CSV file and create Die records"""
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
                        die_number = row.get("die_number", "").strip()
                        dimension1 = row.get("dimension1", "").strip()
                        wt_kg_p_mt = row.get("wt_kg_p_mt", "").strip()

                        if not all([die_number, dimension1, wt_kg_p_mt]):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Missing required fields (die_number, dimension1, wt_kg_p_mt)"
                                )
                            )
                            error_count += 1
                            continue

                        # Convert dimensions and weight
                        try:
                            dimension1_val = Decimal(str(dimension1))
                            wt_kg_p_mt_val = Decimal(str(wt_kg_p_mt))
                        except (ValueError, TypeError):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Invalid numeric values for dimensions or weight"
                                )
                            )
                            error_count += 1
                            continue

                        # Prepare die data
                        die_data = {
                            "die_number": die_number,
                            "dimension1": dimension1_val,
                            "wt_kg_p_mt": wt_kg_p_mt_val,
                            "created_by": default_user,
                        }

                        # Optional fields
                        optional_fields = {
                            "dimension2": "dimension2",
                            "dimension3": "dimension3",
                            "dimension4": "dimension4",
                            "min_wt_kg_p_mt": "min_wt_kg_p_mt",
                            "max_wt_kg_p_mt": "max_wt_kg_p_mt",
                            "description": "description",
                            "die_diagram": "die_diagram",
                            "die_detail_diagram": "die_detail_diagram",
                            "customer_approved_diagram": "customer_approved_diagram",
                            "autocad_drawing": "autocad_drawing",
                            "die_manufacturing": "die_manufacturing",
                            "die_sop": "die_sop",
                            "remarks": "remarks",
                            "customer_reference_number": "customer_reference_number",
                            "die_type": "die_type",
                        }

                        for field_name, csv_key in optional_fields.items():
                            value = row.get(csv_key, "").strip()
                            if value:
                                if field_name in [
                                    "dimension2",
                                    "dimension3",
                                    "dimension4",
                                    "min_wt_kg_p_mt",
                                    "max_wt_kg_p_mt",
                                ]:
                                    try:
                                        die_data[field_name] = Decimal(str(value))
                                    except (ValueError, TypeError):
                                        pass  # Skip invalid decimal values
                                else:
                                    die_data[field_name] = value

                        # Handle foreign key relationships
                        self._set_foreign_keys(die_data, row)

                        # Create or update Die
                        die, created = Die.objects.get_or_create(
                            die_number=die_number, defaults=die_data
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Created Die: {die_number}")
                            )
                        else:
                            # Update existing die with new data
                            for key, value in die_data.items():
                                if key != "created_by":  # Don't overwrite created_by
                                    setattr(die, key, value)
                            die.updated_by = default_user
                            die.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Updated existing Die: {die_number}"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing die {row.get('die_number', 'unknown')}: {e}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nDie data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Updated: {updated_count} existing records\n"
                        f"Errors: {error_count} records failed"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def _set_foreign_keys(self, die_data, row):
        """Set foreign key relationships for Die"""
        # Die Group
        die_group_name = row.get("die_group", "").strip()
        if die_group_name:
            try:
                die_group = DieGroup.objects.get(name=die_group_name)
                die_data["die_group"] = die_group
            except DieGroup.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Die Group not found: {die_group_name}")
                )

        # Die Category
        die_category_name = row.get("die_category", "").strip()
        if die_category_name:
            try:
                die_category = DieCategory.objects.get(name=die_category_name)
                die_data["die_category"] = die_category
            except DieCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Die Category not found: {die_category_name}")
                )

        # Die Sub Category
        die_sub_category_name = row.get("die_sub_category", "").strip()
        if die_sub_category_name:
            try:
                die_sub_category = DieSubCategory.objects.get(
                    name=die_sub_category_name
                )
                die_data["die_sub_category"] = die_sub_category
            except DieSubCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Die Sub Category not found: {die_sub_category_name}"
                    )
                )
