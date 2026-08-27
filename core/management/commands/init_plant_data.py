import csv
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from common.models import Plant, PlantType


class Command(BaseCommand):
    help = "Initialize master data for Plant from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/plant.csv",
            help="Path to CSV file (relative to project root)",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]

        # Always initialize dependencies first
        self.stdout.write(self.style.SUCCESS("Initializing dependencies..."))
        try:
            call_command("init_plant_type_data")
            self.stdout.write(
                self.style.SUCCESS("✓ PlantType data initialized successfully")
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Warning: PlantType initialization failed: {str(e)}"
                )
            )
            self.stdout.write(
                self.style.WARNING("Continuing with Plant initialization...")
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
                error_count = 0

                for row_num, row in enumerate(reader, start=1):
                    plant_code = row.get("plant_code", "").strip()
                    plant_name = row.get("plant_name", "").strip()

                    if not plant_code or not plant_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {row_num}: Skipping row with empty plant_code or plant_name: {row}"
                            )
                        )
                        continue

                    try:
                        # Prepare plant data
                        plant_data = {
                            "plant_code": plant_code,
                            "plant_name": plant_name,
                            "status": row.get("status", "Active").strip(),
                            "address_line_1": row.get("address_line_1", "").strip(),
                            "city": row.get("city", "").strip(),
                            "state": row.get("state", "").strip(),
                            "country": row.get("country", "").strip(),
                            "postal_code": row.get("postal_code", "").strip(),
                            "phone_number": row.get("phone_number", "").strip(),
                            "email": row.get("email", "").strip(),
                            "deleted": False,
                        }

                        # Add optional address_line_2
                        address_line_2 = row.get("address_line_2", "").strip()
                        if address_line_2:
                            plant_data["address_line_2"] = address_line_2

                        # Handle PlantType foreign key
                        plant_type_code = row.get("planttype", "").strip().upper()
                        if plant_type_code:
                            try:
                                plant_type = PlantType.objects.filter(
                                    code=plant_type_code, is_deleted=False
                                ).first()
                                if plant_type:
                                    plant_data["plant_type"] = plant_type
                                else:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f"Row {row_num}: PlantType '{plant_type_code}' not found"
                                        )
                                    )
                                    error_count += 1
                                    continue
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"Row {row_num}: Error looking up PlantType '{plant_type_code}': {str(e)}"
                                    )
                                )
                                error_count += 1
                                continue
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Row {row_num}: plant_type is required"
                                )
                            )
                            error_count += 1
                            continue

                        # Create or get existing plant
                        obj, created = Plant.objects.get_or_create(
                            plant_code=plant_code, defaults=plant_data
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created Plant: {plant_code} - {plant_name}"
                                )
                            )
                        else:
                            existing_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Plant already exists: {plant_code} - {plant_name}"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error processing plant {plant_code}: {str(e)}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nPlant data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present\n"
                        f"Errors: {error_count} records failed"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
