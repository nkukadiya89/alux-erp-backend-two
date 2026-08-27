import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from common.models import Plant, StoreType
from store.models import Store


class Command(BaseCommand):
    help = "Initialize Store data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/store.csv",
            help="Path to Store CSV file (relative to project root)",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]

        # Construct the full path
        if not os.path.isabs(csv_file_path):
            csv_file_path = os.path.join(settings.BASE_DIR, csv_file_path)

        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.ERROR(f"Store CSV file not found: {csv_file_path}")
            )
            return

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                created_count = 0
                existing_count = 0
                error_count = 0

                for row_num, row in enumerate(reader, start=1):
                    store_code = row.get("store_code", "").strip()
                    store_name = row.get("store_name", "").strip()

                    if not store_code or not store_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {row_num}: Skipping Store row with empty store_code or store_name"
                            )
                        )
                        continue

                    try:
                        # Handle Plant foreign key
                        plant_code = row.get("plant_code", "").strip()
                        if not plant_code:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Row {row_num}: plant_code is required"
                                )
                            )
                            error_count += 1
                            continue

                        try:
                            plant = Plant.objects.filter(
                                plant_code=plant_code, deleted=False
                            ).first()
                            if not plant:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"Row {row_num}: Plant '{plant_code}' not found"
                                    )
                                )
                                error_count += 1
                                continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Row {row_num}: Error looking up Plant '{plant_code}': {str(e)}"
                                )
                            )
                            error_count += 1
                            continue

                        # Handle StoreType foreign key
                        store_type_obj = None
                        store_type_name = row.get("store_type", "").strip()
                        if store_type_name:
                            try:
                                store_type_obj = StoreType.objects.filter(
                                    name__iexact=store_type_name
                                ).first()
                                if not store_type_obj:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Row {row_num}: StoreType '{store_type_name}' not found, creating store without store_type"
                                        )
                                    )
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_num}: Error looking up StoreType '{store_type_name}': {str(e)}"
                                    )
                                )

                        # Handle allows_negative_stock
                        allows_negative_stock = (
                            row.get("allows_negative_stock", "False").strip().lower()
                        )
                        allows_negative = allows_negative_stock in [
                            "true",
                            "1",
                            "yes",
                            "y",
                        ]

                        # Create or get existing store
                        obj, created = Store.objects.get_or_create(
                            store_code=store_code,
                            defaults={
                                "store_name": store_name,
                                "store_type": store_type_obj,
                                "plant": plant,
                                "allows_negative_stock": allows_negative,
                            },
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created Store: {store_code} - {store_name}"
                                )
                            )
                        else:
                            existing_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Store already exists: {store_code} - {store_name}"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing store {store_code}: {str(e)}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Store initialization complete! Created: {created_count}, Existing: {existing_count}, Errors: {error_count}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error reading Store CSV file: {str(e)}")
            )
