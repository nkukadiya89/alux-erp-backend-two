import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from common.models import ItemCategory


class Command(BaseCommand):
    help = "Initialize master data for ItemCategory from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/item_category_data.csv",
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
                    category_code = row.get("category_code", "").strip()
                    category_name = row.get("category_name", "").strip()
                    allowed_item_type = row.get("allowed_item_type", "").strip()
                    description = row.get("description", "").strip()
                    status = row.get("status", "").strip()
                    if not category_code or not category_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with missing category_code or category_name: {row}"
                            )
                        )
                        continue

                    # Create or get existing ItemCategory
                    obj, created = ItemCategory.objects.get_or_create(
                        category_code=category_code,
                        defaults={
                            "category_name": category_name,
                            "allowed_item_type": allowed_item_type,
                            "description": description if description else None,
                            "status": "Active",
                            "is_archived": False,
                        },
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created ItemCategory: {category_code} - {category_name}"
                            )
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"ItemCategory already exists: {category_code}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nItem Category data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
