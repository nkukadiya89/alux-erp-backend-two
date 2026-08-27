"""
Debug command to test plant import and identify issues
Usage: python manage.py debug_plant_import
"""

import logging
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from common.models import Plant
from imports.services.plant_importer import PlantImporter
from user.models import User

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("imports")
logger.setLevel(logging.DEBUG)


class Command(BaseCommand):
    help = "Debug plant import to identify issues"

    def handle(self, *args, **options):
        # Get or create a test user
        user, _ = User.objects.get_or_create(
            email="test@example.com",
            defaults={
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        # Read the CSV file
        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "test_data", "plants_valid.csv"
        )
        self.stdout.write(f"Reading CSV from: {csv_path}")

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at: {csv_path}"))
            return

        with open(csv_path, "rb") as f:
            file_content = f.read()
            file = SimpleUploadedFile(
                "plants_valid.csv", file_content, content_type="text/csv"
            )

            self.stdout.write("\n=== Starting Import ===")
            importer = PlantImporter(file, user=user, dry_run=False)

            # Step by step debugging
            self.stdout.write("\n1. Validating file...")
            is_valid, error = importer.validate_file()
            self.stdout.write(f"   File valid: {is_valid}, Error: {error}")

            if not is_valid:
                self.stdout.write(self.style.ERROR(f"File validation failed: {error}"))
                return

            self.stdout.write("\n2. Creating import log...")
            log = importer.create_import_log()
            self.stdout.write(f"   Import log created: {log.id}")

            self.stdout.write("\n3. Parsing file...")
            success, error = importer.parse_file()
            self.stdout.write(f"   Parse success: {success}, Error: {error}")

            if not success:
                self.stdout.write(self.style.ERROR(f"Parse failed: {error}"))
                return

            self.stdout.write(f"   Total rows: {importer.parser.get_row_count()}")
            columns = importer.parser.get_column_names()
            self.stdout.write(f"   Columns ({len(columns)}): {columns}")

            self.stdout.write("\n4. Getting first row...")
            rows = importer.parser.get_rows()
            if rows:
                self.stdout.write(f"   Total rows parsed: {len(rows)}")
                self.stdout.write(f"   First row keys: {list(rows[0].keys())}")
                first_row_sample = dict(list(rows[0].items())[:3])
                self.stdout.write(f"   First row sample: {first_row_sample}")

                self.stdout.write("\n5. Checking field mapping...")
                field_mapping = importer.get_field_mapping()
                self.stdout.write(
                    f"   Field mapping keys: {list(field_mapping.keys())[:5]}..."
                )

                # Check if columns match
                missing_cols = []
                for col_name in field_mapping.keys():
                    if col_name not in rows[0]:
                        missing_cols.append(col_name)
                if missing_cols:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   Missing columns in row: {missing_cols[:3]}..."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS("   All mapped columns found in row")
                    )

                self.stdout.write("\n6. Validating first row...")
                is_valid, errors = importer.validate_row(rows[0], 1)
                self.stdout.write(f"   Valid: {is_valid}, Errors: {len(errors)}")
                if errors:
                    self.stdout.write(self.style.ERROR(f"   Error details:"))
                    for err in errors[:3]:
                        self.stdout.write(
                            f"     - {err.get('field')}: {err.get('message')}"
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS("   First row validation passed")
                    )

                self.stdout.write("\n7. Transforming first row...")
                try:
                    transformed = importer.transform_row_data(rows[0])
                    self.stdout.write(
                        f"   Transformed keys: {list(transformed.keys())[:5]}..."
                    )
                    self.stdout.write(f"   Sample values:")
                    self.stdout.write(
                        f"     plant_code: {transformed.get('plant_code')}"
                    )
                    self.stdout.write(
                        f"     plant_name: {transformed.get('plant_name')}"
                    )
                    self.stdout.write(
                        f"     plant_type: {transformed.get('plant_type')}"
                    )
                    self.stdout.write(f"     status: {transformed.get('status')}")
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"   Transformation error: {str(e)}")
                    )
                    import traceback

                    traceback.print_exc()

            self.stdout.write("\n8. Validating all rows...")
            valid_count, error_count = importer.validate_all_rows()
            self.stdout.write(f"   Valid: {valid_count}, Errors: {error_count}")
            self.stdout.write(
                f"   Validated data count: {len(importer.validated_data)}"
            )

            if importer.validated_data:
                first_valid = importer.validated_data[0]
                self.stdout.write(f"   First validated data sample:")
                for key in list(first_valid.keys())[:5]:
                    self.stdout.write(f"     {key}: {first_valid.get(key)}")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "   No validated data - all rows failed or weren't processed"
                    )
                )

            self.stdout.write("\n9. Checking for existing plants...")
            if importer.validated_data:
                plant_codes = [
                    d.get("plant_code")
                    for d in importer.validated_data
                    if d.get("plant_code")
                ]
                existing = Plant.objects.filter(plant_code__in=plant_codes).values_list(
                    "plant_code", flat=True
                )
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   Found {len(existing)} existing plants: {list(existing)[:3]}..."
                        )
                    )
                    self.stdout.write(
                        "   These will fail unique constraint during save"
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "   No existing plants found - should import successfully"
                        )
                    )

            self.stdout.write("\n10. Saving data...")
            if not importer.dry_run and valid_count > 0:
                try:
                    saved_count = importer.save_data()
                    self.stdout.write(
                        self.style.SUCCESS(f"   Saved: {saved_count} records")
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   Save error: {str(e)}"))
                    import traceback

                    traceback.print_exc()
            else:
                self.stdout.write(
                    f"   Skipping save (dry_run={importer.dry_run}, valid_count={valid_count})"
                )

            self.stdout.write("\n11. Running full import (with fresh file)...")
            # Re-read file for full import test since previous file was consumed
            with open(csv_path, "rb") as f:
                file_content = f.read()
                file2 = SimpleUploadedFile(
                    "plants_valid.csv", file_content, content_type="text/csv"
                )
                importer2 = PlantImporter(file2, user=user, dry_run=False)
                result = importer2.import_data()

            self.stdout.write(f"\n=== Full Import Result ===")
            self.stdout.write(f"Success: {result['success']}")
            self.stdout.write(f"Message: {result['message']}")
            self.stdout.write(f"Total rows: {result['total_rows']}")
            self.stdout.write(f"Success count: {result['success_count']}")
            self.stdout.write(f"Error count: {result['error_count']}")

            # Check database
            self.stdout.write(f"\n=== Database Check ===")
            plant_count = Plant.objects.filter(plant_code__startswith="PLANT-").count()
            self.stdout.write(f"Plants with PLANT- prefix: {plant_count}")

            # Check import log errors
            if importer.import_log:
                error_rows = importer.import_log.error_rows.all()
                if error_rows.exists():
                    self.stdout.write(f"\n=== Import Errors ({error_rows.count()}) ===")
                    for err in error_rows[:5]:
                        self.stdout.write(f"Row {err.row_number}: {err.error_message}")
