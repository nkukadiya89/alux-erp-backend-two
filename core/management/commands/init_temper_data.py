import csv
import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from common.models import UOM, SectionType, YieldUnit
from product.models import Temper


class Command(BaseCommand):
    help = (
        "Initialize master data for Temper from CSV file with foreign key dependencies"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/temper.csv",
            help="Path to CSV file (relative to project root)",
        )
        parser.add_argument(
            "--init-dependencies",
            action="store_true",
            help="Initialize foreign key dependencies first (SectionType, UOM, YieldUnit)",
        )

    def handle(self, *args, **options):
        # Initialize dependencies first if requested
        if options["init_dependencies"]:
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

                for row_num, row in enumerate(reader, start=2):
                    try:
                        with transaction.atomic():
                            temper_data = self.process_row(row)
                            if temper_data:
                                obj, created = Temper.objects.get_or_create(
                                    name=temper_data["name"], defaults=temper_data
                                )

                                if created:
                                    created_count += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"Created Temper: {temper_data['name']}"
                                        )
                                    )
                                else:
                                    # Update existing record with new data
                                    for key, value in temper_data.items():
                                        if key != "name":
                                            setattr(obj, key, value)
                                    obj.save()
                                    existing_count += 1
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Updated existing Temper: {temper_data['name']}"
                                        )
                                    )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error processing row {row_num}: {str(e)}"
                            )
                        )
                        self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                        continue

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nTemper data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Updated: {existing_count} existing records\n"
                        f"Errors: {error_count} records with errors"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def init_dependencies(self):
        """Initialize foreign key dependencies"""
        self.stdout.write(
            self.style.SUCCESS("Initializing foreign key dependencies...")
        )

        # Initialize SectionType
        self.stdout.write("Initializing SectionType...")
        from django.core.management import call_command

        try:
            call_command("init_section_type_data")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"SectionType initialization failed: {str(e)}")
            )

        # Initialize UOM
        self.stdout.write("Initializing UOM...")
        try:
            call_command("init_uom_data")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"UOM initialization failed: {str(e)}")
            )

        # Initialize YieldUnit
        self.stdout.write("Initializing YieldUnit...")
        try:
            call_command("init_yield_unit_data")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"YieldUnit initialization failed: {str(e)}")
            )

    def process_row(self, row):
        """Process a CSV row and return cleaned data"""
        name = row.get("name", "").strip()

        if not name:
            self.stdout.write(
                self.style.WARNING(f"Skipping row with empty name: {row}")
            )
            return None

        # Get foreign key objects
        section_type = None
        section_type_name = row.get("section_type", "").strip()
        if section_type_name:
            try:
                section_type = SectionType.objects.get(name=section_type_name)
            except SectionType.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"SectionType '{section_type_name}' not found for temper '{name}'"
                    )
                )

        dimention_unit = None
        dimention_unit_code = row.get("dimention_unit", "").strip()
        if dimention_unit_code:
            try:
                dimention_unit = UOM.objects.get(uom_code=dimention_unit_code)
            except UOM.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"UOM '{dimention_unit_code}' not found for temper '{name}'"
                    )
                )

        yield_unit = None
        yield_unit_name = row.get("yield_unit", "").strip()
        if yield_unit_name:
            try:
                yield_unit = YieldUnit.objects.get(name=yield_unit_name)
            except YieldUnit.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"YieldUnit '{yield_unit_name}' not found for temper '{name}'"
                    )
                )

        # Helper function to convert to decimal
        def to_decimal(value):
            if not value or value.strip() == "":
                return None
            try:
                return Decimal(str(value))
            except:
                return None

        # Build temper data
        temper_data = {
            "name": name,
            "section_type": section_type,
            "area": row.get("area", "").strip(),
            "dimention_unit": dimention_unit,
            "elongation_50mm_min": to_decimal(row.get("elongation_50mm_min")),
            "elongation_min": to_decimal(row.get("elongation_min")),
            "hardness": to_decimal(row.get("hardness")),
            "section_thickness_over": row.get("section_thickness_over", "").strip()
            or None,
            "section_thickness_upto": row.get("section_thickness_upto", "").strip()
            or None,
            "tensile_min": to_decimal(row.get("tensile_min")),
            "tensile_max": to_decimal(row.get("tensile_max")),
            "yield_min": to_decimal(row.get("yield_min")),
            "yield_max": to_decimal(row.get("yield_max")),
            "yield_unit": yield_unit,
            "electrical_conductivity_min": to_decimal(
                row.get("electrical_conductivity_min")
            ),
            "electrical_conductivity_max": to_decimal(
                row.get("electrical_conductivity_max")
            ),
            "heat_treatment": row.get("heat_treatment", "").strip() or None,
            "temper_code_old": row.get("temper_code_old", "").strip() or None,
            "temper_code_new": row.get("temper_code_new", "").strip() or None,
            "deleted": False,
        }

        return temper_data
