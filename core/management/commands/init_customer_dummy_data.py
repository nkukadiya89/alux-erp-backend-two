import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from customer.models import Customer


class Command(BaseCommand):
    help = "Initialize dummy customer data for ConversionRate testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/customer_dummy_data.csv",
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

                for row in reader:
                    customer_name = row.get("customer_name", "").strip()
                    person_name = row.get("person_name", "").strip()
                    phone_number = row.get("phone_number", "").strip()
                    email = row.get("email", "").strip()
                    # customer_number = row.get("customer_number", "").strip()
                    gstin_number = row.get("gstin_number", "").strip()
                    pan_number = row.get("pan_number", "").strip()

                    if not customer_name or not phone_number:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with missing required fields: {row}"
                            )
                        )
                        continue

                    # Create or get existing customer
                    obj, created = Customer.objects.get_or_create(
                        customer_name=customer_name,
                        defaults={
                            "person_name": person_name,
                            "phone_number": phone_number,
                            "email": email if email else None,
                            # "customer_number": (
                            #     customer_number if customer_number else None
                            # ),
                            "gstin_number": gstin_number if gstin_number else None,
                            "pan_number": pan_number if pan_number else None,
                        },
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Created Customer: {customer_name}")
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Customer already exists: {customer_name}"
                            )
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nCustomer dummy data initialization complete!\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
