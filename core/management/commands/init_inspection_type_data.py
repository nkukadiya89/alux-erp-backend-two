"""
Initialize Inspection Type Master from CSV
"""

import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from common.models import InspectionType, Plant


class Command(BaseCommand):
    help = "Initialize Inspection Type master data from CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/inspection_type.csv",
            help="Path to CSV file (relative to project root)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all non-archived InspectionTypes before creating.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        reset = options.get("reset", False)

        if reset:
            count, _ = InspectionType.objects.filter(is_archived=False).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {count} existing InspectionType(s).")
            )

        if not os.path.isabs(csv_path):
            csv_path = os.path.join(settings.BASE_DIR, csv_path)

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV not found: {csv_path}"))
            return

        created = 0
        existing = 0

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("code") or "").strip().upper()
                name = (row.get("name") or "").strip()
                if not code or not name:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping row with missing code/name: {row}"
                        )
                    )
                    continue

                process_stage = (row.get("process_stage") or "").strip().upper()
                if process_stage not in [
                    c[0] for c in InspectionType.PROCESS_STAGE_CHOICES
                ]:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Invalid process_stage '{process_stage}' for {code}, skipping"
                        )
                    )
                    continue

                requires_sampling = str(
                    row.get("requires_sampling", "false")
                ).strip().lower() in ("true", "1", "yes", "y")
                requires_lab_test = str(
                    row.get("requires_lab_test", "false")
                ).strip().lower() in ("true", "1", "yes", "y")
                is_active = str(row.get("is_active", "true")).strip().lower() in (
                    "true",
                    "1",
                    "yes",
                    "y",
                )
                description = (row.get("description") or "").strip() or None
                plant_code = (row.get("plant_code") or "").strip()
                plant = None
                if plant_code:
                    plant = Plant.objects.filter(
                        plant_code__iexact=plant_code, deleted=False
                    ).first()

                obj, created_flag = InspectionType.objects.get_or_create(
                    code=code,
                    is_archived=False,
                    defaults={
                        "name": name,
                        "process_stage": process_stage,
                        "requires_sampling": requires_sampling,
                        "requires_lab_test": requires_lab_test,
                        "plant": plant,
                        "description": description,
                        "is_active": is_active,
                    },
                )
                if created_flag:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Created InspectionType: {code} - {name}")
                    )
                else:
                    existing += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nInspection Type init complete. Created: {created}, Existing: {existing}"
            )
        )
