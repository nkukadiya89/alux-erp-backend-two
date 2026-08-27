import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from common.models import PackingMode


class Command(BaseCommand):
    help = "Load packing mode data from CSV file into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/packing_mode_data.csv",
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
                    name = row.get("name", "").strip()
                    description = row.get("description", "").strip()

                    if not name:
                        self.stdout.write(
                            self.style.WARNING(f"Skipping row with empty name: {row}")
                        )
                        continue

                    # Create or get existing packing mode
                    obj, created = PackingMode.objects.get_or_create(
                        name=name, defaults={"description": description}
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created PackingMode: {name}")
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"PackingMode already exists: {name}")
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nPacking Mode data loading complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
