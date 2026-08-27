import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from common.models import JobWorkType


class Command(BaseCommand):
    help = "Initialize master data for JobWorkType from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/jobwork_type.csv",
            help="Path to CSV file (relative to project root)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing JobWorkTypes before creating new ones.",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        reset = options.get("reset", False)

        if reset:
            deleted_count, _ = JobWorkType.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} existing JobWorkType(s).")
            )

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
                    discription = row.get("discription", "").strip() or None

                    if not name:
                        self.stdout.write(
                            self.style.WARNING(f"Skipping row with empty name: {row}")
                        )
                        continue

                    obj, created = JobWorkType.objects.get_or_create(
                        name=name,
                        defaults={"discription": discription},
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created JobWorkType: {name}")
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"JobWorkType already exists: {name}")
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nJob Work Type data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
