import csv
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from common.models import Department, Plant


class Command(BaseCommand):
    """
    Management command to initialize Department master data from CSV file.

    Usage:
        python manage.py init_department_data
        python manage.py init_department_data --file path/to/custom.csv
    """

    help = "Initialize Department master data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="core/management/source/department.csv",
            help="Path to CSV file containing department data",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records if they exist",
        )

    def handle(self, *args, **options):
        csv_file_path = options["file"]
        update_existing = options["update"]

        # Always initialize dependencies first
        self.stdout.write(self.style.SUCCESS("Initializing dependencies..."))
        try:
            # This will automatically call init_plant_type_data as well
            call_command("init_plant_data")
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Plant and PlantType data initialized successfully"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Warning: Plant initialization failed: {str(e)}")
            )
            self.stdout.write(
                self.style.WARNING("Continuing with Department initialization...")
            )

        # Construct full path
        if not os.path.isabs(csv_file_path):
            csv_file_path = os.path.join(settings.BASE_DIR, csv_file_path)

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        try:
            with transaction.atomic():
                self.load_departments_from_csv(csv_file_path, update_existing)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error loading department data: {str(e)}")
            )
            raise

    def load_departments_from_csv(self, csv_file_path, update_existing):
        """Load department data from CSV file"""

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write(f"Loading department data from: {csv_file_path}")

        with open(csv_file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Clean and validate required fields
                    department_code = (
                        row["department_code"].strip().upper()
                        if row["department_code"]
                        else None
                    )
                    department_name = (
                        row["department_name"].strip()
                        if row["department_name"]
                        else None
                    )
                    department_type = (
                        row["department_type"].strip().upper()
                        if row["department_type"]
                        else None
                    )

                    if not all([department_code, department_name, department_type]):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {row_num}: Missing required fields (code, name, or type). Skipping."
                            )
                        )
                        skipped_count += 1
                        continue

                    # Validate department type
                    valid_types = [
                        choice[0] for choice in Department.DEPARTMENT_TYPE_CHOICES
                    ]
                    if department_type not in valid_types:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Row {row_num}: Invalid department_type "{department_type}". '
                                f"Valid options: {valid_types}. Skipping."
                            )
                        )
                        skipped_count += 1
                        continue

                    # Handle plant foreign key
                    plant = None
                    plant_code = row.get("plant_code", "").strip().upper()
                    if plant_code:
                        try:
                            plant = Plant.objects.get(
                                plant_code__iexact=plant_code,
                                status="Active",
                                deleted=False,
                            )
                        except Plant.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Row {row_num}: Plant with code "{plant_code}" not found. '
                                    "Department will be created without plant assignment."
                                )
                            )

                    # Handle parent department
                    parent_department = None
                    parent_code = row.get("parent_department_code", "").strip().upper()
                    if parent_code:
                        try:
                            parent_department = Department.objects.get(
                                department_code__iexact=parent_code,
                                status="Active",
                                is_archived=False,
                            )
                        except Department.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Row {row_num}: Parent department "{parent_code}" not found. '
                                    "Department will be created without parent."
                                )
                            )

                    # Prepare data
                    department_data = {
                        "department_name": department_name,
                        "department_type": department_type,
                        "plant": plant,
                        "cost_center_code": row.get("cost_center_code", "").strip()
                        or None,
                        "parent_department": parent_department,
                        "status": row.get("status", "Active").strip(),
                        "is_archived": row.get("is_archived", "").strip().lower()
                        in ["true", "1", "yes"],
                    }

                    # Check if department exists
                    department, created = Department.objects.get_or_create(
                        department_code=department_code, defaults=department_data
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Created department: {department_code} - {department_name}"
                            )
                        )
                    else:
                        if update_existing:
                            # Update existing department
                            for field, value in department_data.items():
                                setattr(department, field, value)
                            department.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"↻ Updated department: {department_code} - {department_name}"
                                )
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠ Department {department_code} already exists. Use --update to modify."
                                )
                            )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Row {row_num}: Error processing department {row.get("department_code", "UNKNOWN")}: {str(e)}'
                        )
                    )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"Department Data Load Summary:"))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")
        self.stdout.write(f"  Errors: {error_count}")
        self.stdout.write("=" * 60)

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠ {error_count} errors encountered. Please check the data and try again."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Department data loaded successfully!")
            )
