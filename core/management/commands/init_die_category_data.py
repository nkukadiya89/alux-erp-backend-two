import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from die.models import DieSubCategory


class Command(BaseCommand):
    help = "Initialize master data for DieSubCategory from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/die_sub_category.csv",
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

                    if not name:
                        self.stdout.write(
                            self.style.WARNING(f"Skipping row with empty name: {row}")
                        )
                        continue

                    # Create or get existing die category
                    obj, created = DieSubCategory.objects.get_or_create(name=name)

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created DieSubCategory: {name}")
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"DieSubCategory already exists: {name}")
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nDie Category data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
