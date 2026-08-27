import csv
import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from die.models import DiePress


class Command(BaseCommand):
    help = "Initialize master data for DiePress from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/die_press.csv",
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

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                created_count = 0
                existing_count = 0

                for row in reader:
                    code = row.get("code", "").strip()
                    name = row.get("name", "").strip()

                    if not code or not name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with empty code or name: {row}"
                            )
                        )
                        continue

                    # Prepare data with proper type conversion
                    press_data = {
                        "code": code,
                        "name": name,
                    }

                    # Convert numeric fields safely
                    numeric_fields = [
                        "capacity",
                        "billet_diameter",
                        "billet_length_min",
                        "billet_length_max",
                        "billet_weight",
                        "extrusion_length_min",
                        "extrusion_length_max",
                    ]

                    decimal_fields = ["billet_wt_factor"]

                    for field in numeric_fields:
                        value = row.get(field, "").strip()
                        if value:
                            try:
                                press_data[field] = float(value)
                            except (ValueError, TypeError):
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Invalid {field} value '{value}' for {name}, skipping field"
                                    )
                                )

                    for field in decimal_fields:
                        value = row.get(field, "").strip()
                        if value:
                            try:
                                press_data[field] = Decimal(value)
                            except (ValueError, TypeError):
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Invalid {field} value '{value}' for {name}, skipping field"
                                    )
                                )

                    # Create or get existing die press
                    obj, created = DiePress.objects.get_or_create(
                        code=code, defaults=press_data
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created DiePress: {code} - {name}")
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"DiePress already exists: {code} - {name}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nDie Press data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
