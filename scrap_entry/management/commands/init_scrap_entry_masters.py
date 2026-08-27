"""
Initialize ScrapType and Process master data for Scrap Entry module.
Aluminum extrusion manufacturing: scrap types and production processes.
"""

import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from scrap_entry.models import Process, ScrapType


# Default ScrapType data (code, name) – aluminum extrusion scrap categories
DEFAULT_SCRAP_TYPES = [
    ("EXT-SCRAP", "Extrusion Scrap"),
    ("CUT-SCRAP", "Cutting Scrap"),
    ("PRESS-SCRAP", "Press Scrap"),
    ("BILLET-END", "Billet End"),
    ("SKULL", "Skull / Furnace Skull"),
    ("DROSS", "Dross"),
    ("SLUDGE", "Sludge"),
    ("TURNINGS", "Turnings"),
    ("BURRS", "Burrs"),
    ("OFFCUT", "Offcut"),
    ("DEFECTIVE", "Defective / Rejected"),
    ("PACKAGING-SCRAP", "Packaging Scrap"),
]

# Default Process data (code, name) – production process sources
DEFAULT_PROCESSES = [
    ("EXTRUSION", "Extrusion"),
    ("CUTTING", "Cutting"),
    ("PRESS", "Press"),
    ("MELTING", "Melting"),
    ("CASTING", "Casting"),
    ("ANODIZING", "Anodizing"),
    ("POWDER-COAT", "Powder Coating"),
    ("FABRICATION", "Fabrication"),
    ("ASSEMBLY", "Assembly"),
    ("QUALITY-CHECK", "Quality Check"),
    ("PACKING", "Packing"),
    ("DISPATCH", "Dispatch"),
    ("MAINTENANCE", "Maintenance"),
    ("TOOL-ROOM", "Tool Room"),
]


class Command(BaseCommand):
    help = "Initialize ScrapType and Process master data for Scrap Entry (aluminum extrusion ERP)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-dir",
            type=str,
            default=None,
            help="Directory containing scrap_type.csv and process.csv (relative to BASE_DIR). e.g. scrap_entry/management/source. If not set, uses default inline data.",
        )
        parser.add_argument(
            "--use-app-csv",
            action="store_true",
            help="Load from scrap_entry/management/source/ (scrap_type.csv, process.csv).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing ScrapTypes and Processes before creating (use with care).",
        )
        parser.add_argument(
            "--scrap-only",
            action="store_true",
            help="Only load ScrapType data.",
        )
        parser.add_argument(
            "--process-only",
            action="store_true",
            help="Only load Process data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options.get("reset", False)
        scrap_only = options.get("scrap_only", False)
        process_only = options.get("process_only", False)
        csv_dir = options.get("csv_dir")
        if options.get("use_app_csv") and not csv_dir:
            csv_dir = os.path.join("scrap_entry", "management", "source")

        if reset:
            if not process_only:
                n_st, _ = ScrapType.objects.all().delete()
                self.stdout.write(self.style.WARNING(f"Deleted {n_st} ScrapType(s)."))
            if not scrap_only:
                n_pr, _ = Process.objects.all().delete()
                self.stdout.write(self.style.WARNING(f"Deleted {n_pr} Process(es)."))

        created_st = 0
        existing_st = 0
        created_pr = 0
        existing_pr = 0

        if not process_only:
            if csv_dir:
                scrap_path = os.path.join(settings.BASE_DIR, csv_dir, "scrap_type.csv")
                created_st, existing_st = self._load_scrap_types_from_csv(scrap_path)
            else:
                created_st, existing_st = self._load_scrap_types_default()

        if not scrap_only:
            if csv_dir:
                process_path = os.path.join(settings.BASE_DIR, csv_dir, "process.csv")
                created_pr, existing_pr = self._load_processes_from_csv(process_path)
            else:
                created_pr, existing_pr = self._load_processes_default()

        self.stdout.write(
            self.style.SUCCESS(
                "\nScrap Entry masters initialization complete!\n"
                f"ScrapType: created={created_st}, existing={existing_st}\n"
                f"Process:   created={created_pr}, existing={existing_pr}"
            )
        )

    def _load_scrap_types_default(self):
        created = 0
        existing = 0
        for code, name in DEFAULT_SCRAP_TYPES:
            obj, is_new = ScrapType.objects.get_or_create(
                code=code.strip().upper(),
                defaults={"name": name, "is_archived": False},
            )
            if is_new:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created ScrapType: {obj.code} - {obj.name}")
                )
            else:
                existing += 1
        return created, existing

    def _load_scrap_types_from_csv(self, csv_file_path):
        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.WARNING(
                    f"ScrapType CSV not found: {csv_file_path}, using defaults."
                )
            )
            return self._load_scrap_types_default()

        created = 0
        existing = 0
        with open(csv_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("code") or "").strip().upper()
                name = (row.get("name") or "").strip()
                if not code:
                    continue
                category_code = (row.get("category_code") or "").strip() or None
                category = None
                if category_code:
                    from common.models import ItemCategory

                    category = ItemCategory.objects.filter(
                        category_code=category_code, is_archived=False
                    ).first()
                obj, is_new = ScrapType.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": name or code,
                        "category": category,
                        "is_archived": False,
                    },
                )
                if is_new:
                    created += 1
                else:
                    existing += 1
        return created, existing

    def _load_processes_default(self):
        created = 0
        existing = 0
        for code, name in DEFAULT_PROCESSES:
            obj, is_new = Process.objects.get_or_create(
                code=code.strip().upper(),
                defaults={"name": name, "is_archived": False},
            )
            if is_new:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created Process: {obj.code} - {obj.name}")
                )
            else:
                existing += 1
        return created, existing

    def _load_processes_from_csv(self, csv_file_path):
        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.WARNING(
                    f"Process CSV not found: {csv_file_path}, using defaults."
                )
            )
            return self._load_processes_default()

        created = 0
        existing = 0
        with open(csv_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("code") or "").strip().upper()
                name = (row.get("name") or "").strip()
                if not code:
                    continue
                obj, is_new = Process.objects.get_or_create(
                    code=code,
                    defaults={"name": name or code, "is_archived": False},
                )
                if is_new:
                    created += 1
                else:
                    existing += 1
        return created, existing
