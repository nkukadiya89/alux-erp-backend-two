"""
Django management command to test Temper bulk import
Usage: python manage.py test_temper_import
"""

import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from imports.services.temper_importer import TemperImporter
from user.models import User


class Command(BaseCommand):
    help = "Test Temper bulk import with CSV file"

    def handle(self, *args, **options):
        # Get the first user
        user = User.objects.first()
        if not user:
            self.stdout.write(
                self.style.ERROR("No user found. Please create a user first.")
            )
            return

        # Path to test CSV file
        csv_file_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "imports",
            "test_data",
            "temper",
            "temper_valid.csv",
        )

        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.ERROR(f"Test CSV file not found at: {csv_file_path}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Testing Temper bulk import with file: {csv_file_path}")
        )
        self.stdout.write(
            f"User: {user.email if hasattr(user, 'email') else user.username}"
        )
        self.stdout.write("-" * 80)

        # Read CSV file
        with open(csv_file_path, "rb") as f:
            file_content = f.read()

        # Create SimpleUploadedFile
        uploaded_file = SimpleUploadedFile(
            name="temper_valid.csv", content=file_content, content_type="text/csv"
        )

        # Test with dry_run=True first (validation only)
        self.stdout.write("\n1. Testing with dry_run=True (validation only)...")
        importer = TemperImporter(uploaded_file, user=user, dry_run=True)
        result = importer.import_data()

        self.stdout.write(f"Success: {result.get('success')}")
        self.stdout.write(f"Message: {result.get('message')}")
        if "data" in result:
            data = result["data"]
            self.stdout.write(f"Total Records: {data.get('total_records', 0)}")
            self.stdout.write(f"Inserted: {data.get('inserted', 0)}")
            self.stdout.write(f"Updated: {data.get('updated', 0)}")
            self.stdout.write(f"Skipped: {data.get('skipped', 0)}")
            self.stdout.write(f"Failed: {data.get('failed', 0)}")
            self.stdout.write(f"Success Count: {data.get('success_count', 0)}")
            self.stdout.write(f"Error Count: {data.get('error_count', 0)}")
            if data.get("row_errors"):
                self.stdout.write(f"\nRow Errors (showing first 5):")
                for error in data["row_errors"][:5]:
                    self.stdout.write(
                        f"  Row {error.get('row_number')}: {error.get('errors', [])}"
                    )

        # Reset file for actual import
        uploaded_file.seek(0)

        # Test with dry_run=False (actual import)
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("2. Testing with dry_run=False (actual import)...")
        importer = TemperImporter(uploaded_file, user=user, dry_run=False)
        result = importer.import_data()

        self.stdout.write(f"Success: {result.get('success')}")
        self.stdout.write(f"Message: {result.get('message')}")
        if "data" in result:
            data = result["data"]
            self.stdout.write(f"Total Records: {data.get('total_records', 0)}")
            self.stdout.write(f"Inserted: {data.get('inserted', 0)}")
            self.stdout.write(f"Updated: {data.get('updated', 0)}")
            self.stdout.write(f"Skipped: {data.get('skipped', 0)}")
            self.stdout.write(f"Failed: {data.get('failed', 0)}")
            self.stdout.write(f"Success Count: {data.get('success_count', 0)}")
            self.stdout.write(f"Error Count: {data.get('error_count', 0)}")
            self.stdout.write(f"Import Log ID: {data.get('import_log_id', '')}")
            if data.get("row_errors"):
                self.stdout.write(f"\nRow Errors (showing first 5):")
                for error in data["row_errors"][:5]:
                    self.stdout.write(
                        f"  Row {error.get('row_number')}: {error.get('errors', [])}"
                    )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Test completed!"))
