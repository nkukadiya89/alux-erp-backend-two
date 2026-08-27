import csv
import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from die.models import DieSize


class Command(BaseCommand):
    help = "Initialize master data for DieSize from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/die_size.csv",
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
                    die_height_str = row.get("die_height", "").strip()
                    die_width_str = row.get("die_width", "").strip()

                    if not die_height_str or not die_width_str:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with empty dimensions: {row}"
                            )
                        )
                        continue

                    try:
                        die_height = Decimal(die_height_str)
                        die_width = Decimal(die_width_str)
                    except (ValueError, TypeError) as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Invalid decimal values in row {row}: {e}"
                            )
                        )
                        continue

                    # Create or get existing die size
                    obj, created = DieSize.objects.get_or_create(
                        die_height=die_height, die_width=die_width
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created DieSize: {die_height} x {die_width}"
                            )
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"DieSize already exists: {die_height} x {die_width}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nDie Size data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
