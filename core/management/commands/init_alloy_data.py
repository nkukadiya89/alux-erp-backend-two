import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from product.models import Alloy


class Command(BaseCommand):
    help = "Initialize master data for Alloy from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/alloy.csv",
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
                error_count = 0

                for row_num, row in enumerate(reader, start=1):
                    alloy_code = row.get("alloy_code", "").strip()

                    if not alloy_code:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {row_num}: Skipping row with empty alloy_code: {row}"
                            )
                        )
                        continue

                    try:
                        # Prepare alloy data
                        alloy_data = {
                            "alloy_code": alloy_code,
                            "standard_name": row.get("standard_name", "").strip()
                            or None,
                            "color_code": row.get("color_code", "").strip() or None,
                            "remark": row.get("remark", "").strip() or None,
                        }

                        # Add chemical composition fields if present
                        composition_fields = [
                            "si_min",
                            "si_max",
                            "mg_min",
                            "mg_max",
                            "fe_min",
                            "fe_max",
                            "mn_min",
                            "mn_max",
                            "cu_min",
                            "cu_max",
                            "zn_min",
                            "zn_max",
                            "cr_min",
                            "cr_max",
                            "ti_min",
                            "ti_max",
                            "bi_min",
                            "bi_max",
                            "pb_min",
                            "pb_max",
                            "sn_min",
                            "sn_max",
                            "others_each_min",
                            "others_each_max",
                            "others_total_min",
                            "others_total_max",
                        ]

                        for field in composition_fields:
                            value = row.get(field, "").strip()
                            if value:
                                try:
                                    alloy_data[field] = float(value)
                                except ValueError:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Row {row_num}: Invalid numeric value for {field}: {value}"
                                        )
                                    )

                        # Create or get existing alloy
                        obj, created = Alloy.objects.get_or_create(
                            alloy_code=alloy_code, defaults=alloy_data
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Created Alloy: {alloy_code}")
                            )
                        else:
                            existing_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Alloy already exists: {alloy_code}"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing alloy {alloy_code}: {str(e)}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nAlloy data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present\n"
                        f"Errors: {error_count} records failed"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
