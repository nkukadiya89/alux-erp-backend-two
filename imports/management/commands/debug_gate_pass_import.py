"""
Debug command to test Gate Pass import.
Usage: python manage.py debug_gate_pass_import
"""

import logging
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from imports.services.gate_pass_importer import GatePassImporter
from user.models import User

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("imports.gate_pass")
logger.setLevel(logging.DEBUG)


class Command(BaseCommand):
    help = "Debug Gate Pass import to identify issues"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            email="gatepass-import@example.com",
            defaults={
                "username": "gatepass_import_user",
                "first_name": "Gate",
                "last_name": "Pass",
            },
        )

        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "test_data",
            "gate_pass_valid.csv",
        )
        self.stdout.write(f"Reading CSV from: {csv_path}")

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at: {csv_path}"))
            return

        with open(csv_path, "rb") as f:
            file_content = f.read()
            uploaded = SimpleUploadedFile(
                "gate_pass_valid.csv", file_content, content_type="text/csv"
            )

        importer = GatePassImporter(uploaded, user=user, dry_run=False)

        self.stdout.write("1. Validating file...")
        is_valid, error = importer.validate_file()
        self.stdout.write(f"   File valid: {is_valid}, Error: {error}")
        if not is_valid:
            return

        self.stdout.write("2. Creating import log...")
        log = importer.create_import_log()
        self.stdout.write(f"   Import log created: {log.id}")

        self.stdout.write("3. Parsing file...")
        success, error = importer.parse_file()
        self.stdout.write(f"   Parse success: {success}, Error: {error}")
        if not success:
            return

        self.stdout.write(f"   Total rows: {importer.parser.get_row_count()}")

        self.stdout.write("4. Validating all rows...")
        valid_count, error_count = importer.validate_all_rows()
        self.stdout.write(f"   Valid: {valid_count}, Errors: {error_count}")

        if valid_count:
            self.stdout.write("5. Saving data...")
            saved, failed = importer.save_data()
            self.stdout.write(
                self.style.SUCCESS(f"   Saved records: {saved}, Failed saves: {failed}")
            )

        self.stdout.write("6. Running full import via import_data()...")
        with open(csv_path, "rb") as f:
            file_content = f.read()
            uploaded2 = SimpleUploadedFile(
                "gate_pass_valid.csv", file_content, content_type="text/csv"
            )
        importer2 = GatePassImporter(uploaded2, user=user, dry_run=False)
        result = importer2.import_data()

        self.stdout.write("\n=== Full Import Result ===")
        for key in ["success", "message", "total_rows", "success_count", "error_count"]:
            self.stdout.write(f"{key}: {result.get(key)}")
