import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from melting_furnace.models import AdditiveCategory


class Command(BaseCommand):
    help = "Initialize master data for AdditiveCategory from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/additive_category.csv",
            help="Path to CSV file (relative to project root)",
        )
        parser.add_argument(
            "--reset", action="store_true", help="Delete all before creating."
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        if options.get("reset"):
            n, _ = AdditiveCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {n} AdditiveCategory(s)."))
        if not os.path.isabs(csv_file_path):
            csv_file_path = os.path.join(settings.BASE_DIR, csv_file_path)
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return
        try:
            with open(csv_file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                created_count = existing_count = 0
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        continue
                    _, created = AdditiveCategory.objects.get_or_create(name=name)
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created AdditiveCategory: {name}")
                        )
                    else:
                        existing_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nAdditive Category init complete. Created: {created_count}, Existing: {existing_count}"
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
