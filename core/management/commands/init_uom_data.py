import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from common.models import UOM


class Command(BaseCommand):
    help = "Initialize master data for UOM from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/uom_data.csv",
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
                    uom_code = row.get("uom_code", "").strip()
                    uom_name = row.get("uom_name", "").strip()
                    uom_type = row.get("uom_type", "").strip()
                    decimal_allowed_str = row.get("decimal_allowed", "").strip().lower()

                    if not uom_code or not uom_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with missing uom_code or uom_name: {row}"
                            )
                        )
                        continue

                    decimal_allowed = decimal_allowed_str in ("true", "1", "yes")

                    # Create or get existing UOM
                    obj, created = UOM.objects.get_or_create(
                        uom_code=uom_code,
                        defaults={
                            "uom_name": uom_name,
                            "uom_type": uom_type,
                            "decimal_allowed": decimal_allowed,
                            "is_active": True,
                        },
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created UOM: {uom_code} - {uom_name}")
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"UOM already exists: {uom_code}")
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nUOM data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
