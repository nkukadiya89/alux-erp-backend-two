"""
Debug script to test plant import and identify issues
Run this in Django shell: python manage.py shell < imports/test_import_debug.py
"""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alux_erp.settings")
django.setup()

import logging

from django.core.files.uploadedfile import SimpleUploadedFile

from common.models import Plant
from imports.services.plant_importer import PlantImporter
from user.models import User

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("imports")
logger.setLevel(logging.DEBUG)

# Get or create a test user
user, _ = User.objects.get_or_create(
    email="test@example.com",
    defaults={"username": "testuser", "first_name": "Test", "last_name": "User"},
)

# Read the CSV file
csv_path = os.path.join(os.path.dirname(__file__), "test_data", "plants_valid.csv")
print(f"Reading CSV from: {csv_path}")

with open(csv_path, "rb") as f:
    file_content = f.read()
    file = SimpleUploadedFile("plants_valid.csv", file_content, content_type="text/csv")

    print("\n=== Starting Import ===")
    importer = PlantImporter(file, user=user, dry_run=False)

    # Step by step debugging
    print("\n1. Validating file...")
    is_valid, error = importer.validate_file()
    print(f"   File valid: {is_valid}, Error: {error}")

    print("\n2. Creating import log...")
    log = importer.create_import_log()
    print(f"   Import log created: {log.id}")

    print("\n3. Parsing file...")
    success, error = importer.parse_file()
    print(f"   Parse success: {success}, Error: {error}")

    if success:
        print(f"   Total rows: {importer.parser.get_row_count()}")
        print(f"   Columns: {importer.parser.get_column_names()}")

        print("\n4. Getting first row...")
        rows = importer.parser.get_rows()
        if rows:
            print(f"   First row keys: {list(rows[0].keys())}")
            print(f"   First row sample: {dict(list(rows[0].items())[:3])}")

            print("\n5. Validating first row...")
            is_valid, errors = importer.validate_row(rows[0], 1)
            print(f"   Valid: {is_valid}, Errors: {len(errors)}")
            if errors:
                print(f"   Error details: {errors[:2]}")

            print("\n6. Transforming first row...")
            try:
                transformed = importer.transform_row_data(rows[0])
                print(f"   Transformed keys: {list(transformed.keys())}")
                print(
                    f"   Sample values: plant_code={transformed.get('plant_code')}, plant_name={transformed.get('plant_name')}"
                )
            except Exception as e:
                print(f"   Transformation error: {str(e)}")
                import traceback

                traceback.print_exc()

        print("\n7. Validating all rows...")
        valid_count, error_count = importer.validate_all_rows()
        print(f"   Valid: {valid_count}, Errors: {error_count}")
        print(f"   Validated data count: {len(importer.validated_data)}")

        if importer.validated_data:
            print(
                f"   First validated data: {dict(list(importer.validated_data[0].items())[:5])}"
            )

        print("\n8. Saving data...")
        if not importer.dry_run and valid_count > 0:
            try:
                saved_count = importer.save_data()
                print(f"   Saved: {saved_count} records")
            except Exception as e:
                print(f"   Save error: {str(e)}")
                import traceback

                traceback.print_exc()

    print("\n9. Running full import...")
    result = importer.import_data()
    print(f"\n=== Import Result ===")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Total rows: {result['total_rows']}")
    print(f"Success count: {result['success_count']}")
    print(f"Error count: {result['error_count']}")

    # Check database
    print(f"\n=== Database Check ===")
    plant_count = Plant.objects.filter(plant_code__startswith="PLANT-").count()
    print(f"Plants with PLANT- prefix: {plant_count}")
