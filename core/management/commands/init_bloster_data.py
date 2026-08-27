import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from bloster.models import BlosterMaster
from die.models import DiePress


class Command(BaseCommand):
    help = "Initialize master data for BlosterMaster from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/bloster_master_data.csv",
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

                for row in reader:
                    bloster_no = row.get("bloster_no", "").strip()
                    press_code = row.get("press_code", "").strip()

                    if not bloster_no:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with empty bloster_no: {row}"
                            )
                        )
                        error_count += 1
                        continue

                    # Find the corresponding DiePress by code
                    press_instance = None
                    if press_code:
                        try:
                            press_instance = DiePress.objects.get(
                                code=press_code, deleted=False
                            )
                        except DiePress.DoesNotExist:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"DiePress with code '{press_code}' not found for bloster '{bloster_no}'. Skipping."
                                )
                            )
                            error_count += 1
                            continue

                    # Create or get existing bloster
                    obj, created = BlosterMaster.objects.get_or_create(
                        bloster_no=bloster_no,
                        defaults={
                            "press": press_instance,
                        },
                    )

                    if created:
                        created_count += 1
                        press_info = (
                            f" (Press: {press_code})"
                            if press_instance
                            else " (No Press)"
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created BlosterMaster: {bloster_no}{press_info}"
                            )
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"BlosterMaster already exists: {bloster_no}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nBloster Master data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present\n"
                        f"Errors: {error_count} records skipped due to errors"
                    )
                )

                if error_count > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"\nNote: {error_count} records had errors. Please ensure:\n"
                            f"1. DiePress data is loaded first using 'init_die_press_data' command\n"
                            f"2. All press_code values in CSV match existing DiePress codes"
                        )
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
