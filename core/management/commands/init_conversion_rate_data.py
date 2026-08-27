import csv
import os
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from customer.models import Customer
from die.models import ConversionRate, Die
from product.models import Alloy, Temper


class Command(BaseCommand):
    help = "Initialize master data for ConversionRate from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/conversion_rate_data.csv",
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

        # Always initialize dependencies first
        self._initialize_dependencies()

        # Check for missing dependencies after initialization
        missing_dependencies = self._check_missing_dependencies(csv_file_path)
        if missing_dependencies:
            self.stdout.write(
                self.style.ERROR(
                    f"Missing dependencies found: {missing_dependencies}\n"
                    "Please ensure all dependency data is loaded first."
                )
            )
            return

        self._process_conversion_rates(csv_file_path)

    def _initialize_dependencies(self):
        """Initialize all required dependency commands"""
        dependency_commands = [
            ("init_customer_dummy_data", "Customer data"),
            ("init_alloy_data", "Alloy data"),
            ("init_temper_data", "Temper data"),
            # Note: Die data initialization would need to be added if a command exists
        ]

        self.stdout.write(self.style.WARNING("Initializing dependencies..."))

        for command_name, description in dependency_commands:
            try:
                self.stdout.write(f"  - Initializing {description}...", ending="")
                call_command(command_name, verbosity=0)
                self.stdout.write(self.style.SUCCESS(" ✓"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f" ⚠ (may already exist)"))
                # Continue with other dependencies even if one fails

    def _check_missing_dependencies(self, csv_file_path):
        """Check which required dependencies are missing from the database"""
        missing = {"customers": [], "dies": [], "alloys": [], "tempers": []}

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                # Collect unique values from CSV
                unique_customers = set()
                unique_dies = set()
                unique_alloys = set()
                unique_tempers = set()

                for row in reader:
                    customer_name = row.get("customer_name", "").strip()
                    die_number = row.get("die_number", "").strip()
                    alloy_code = row.get("alloy_code", "").strip()
                    temper_name = row.get("temper_name", "").strip()

                    if customer_name:
                        unique_customers.add(customer_name)
                    if die_number:
                        unique_dies.add(die_number)
                    if alloy_code:
                        unique_alloys.add(alloy_code)
                    if temper_name:
                        unique_tempers.add(temper_name)

                # Check existence in database
                for customer_name in unique_customers:
                    if not Customer.objects.filter(
                        customer_name=customer_name, deleted=False
                    ).exists():
                        missing["customers"].append(customer_name)

                for die_number in unique_dies:
                    if not Die.objects.filter(
                        die_number=die_number, deleted=False
                    ).exists():
                        missing["dies"].append(die_number)

                for alloy_code in unique_alloys:
                    if not Alloy.objects.filter(
                        alloy_code=alloy_code, deleted=False
                    ).exists():
                        missing["alloys"].append(alloy_code)

                for temper_name in unique_tempers:
                    if not Temper.objects.filter(
                        name=temper_name, deleted=False
                    ).exists():
                        missing["tempers"].append(temper_name)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error checking dependencies: {str(e)}")
            )
            return {}

        # Filter out empty lists
        return {k: v for k, v in missing.items() if v}

    def _process_conversion_rates(self, csv_file_path):
        """Process the CSV file and create ConversionRate records"""
        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                created_count = 0
                existing_count = 0
                error_count = 0

                for row_num, row in enumerate(reader, start=1):
                    try:
                        result = self._process_single_row(row, row_num)
                        if result == "created":
                            created_count += 1
                        elif result == "existing":
                            existing_count += 1
                        else:  # error
                            error_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Unexpected error: {str(e)}"
                            )
                        )
                        error_count += 1

                # Summary
                self._print_summary(created_count, existing_count, error_count)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def _process_single_row(self, row, row_num):
        """Process a single CSV row and return 'created', 'existing', or 'error'"""
        customer_name = row.get("customer_name", "").strip()
        die_number = row.get("die_number", "").strip()
        alloy_code = row.get("alloy_code", "").strip()
        temper_name = row.get("temper_name", "").strip()
        conversion_str = row.get("conversion", "").strip()
        remarks = row.get("remarks", "").strip()

        # Validate required fields
        if not all([customer_name, die_number, conversion_str]):
            self.stdout.write(
                self.style.WARNING(
                    f"Row {row_num}: Missing required fields (customer_name, die_number, conversion)"
                )
            )
            return "error"

        # Get foreign key instances
        customer = self._get_customer(customer_name)
        if not customer:
            self.stdout.write(
                self.style.ERROR(f"Row {row_num}: Customer '{customer_name}' not found")
            )
            return "error"

        die = self._get_die(die_number)
        if not die:
            self.stdout.write(
                self.style.ERROR(f"Row {row_num}: Die '{die_number}' not found")
            )
            return "error"

        alloy = self._get_alloy(alloy_code) if alloy_code else None
        temper = self._get_temper(temper_name) if temper_name else None

        # Convert conversion rate
        try:
            conversion = Decimal(conversion_str)
        except (ValueError, TypeError):
            self.stdout.write(
                self.style.ERROR(
                    f"Row {row_num}: Invalid conversion value '{conversion_str}'"
                )
            )
            return "error"

        # Create or get existing conversion rate
        obj, created = ConversionRate.objects.get_or_create(
            customer=customer,
            die=die,
            alloy=alloy,
            temper=temper,
            defaults={
                "conversion": conversion,
                "remarks": remarks if remarks else None,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Row {row_num}: Created ConversionRate: {customer_name} - {die_number} - {conversion}"
                )
            )
            return "created"
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Row {row_num}: ConversionRate already exists: {customer_name} - {die_number}"
                )
            )
            return "existing"

    def _get_customer(self, customer_name):
        """Get customer by name, create if not exists"""
        try:
            return Customer.objects.get(customer_name=customer_name, deleted=False)
        except Customer.DoesNotExist:
            # Try to create customer on the fly as fallback
            return self._create_customer_on_fly(customer_name)

    def _get_die(self, die_number):
        """Get die by number"""
        try:
            return Die.objects.get(die_number=die_number, deleted=False)
        except Die.DoesNotExist:
            return None

    def _get_alloy(self, alloy_code):
        """Get alloy by code"""
        try:
            return Alloy.objects.get(alloy_code=alloy_code, deleted=False)
        except Alloy.DoesNotExist:
            return None

    def _get_temper(self, temper_name):
        """Get temper by name"""
        try:
            return Temper.objects.get(name=temper_name, deleted=False)
        except Temper.DoesNotExist:
            return None

    def _create_customer_on_fly(self, customer_name):
        """Create a basic customer record on the fly as fallback"""
        try:
            customer = Customer.objects.create(
                customer_name=customer_name,
                person_name=f"Contact for {customer_name}",
                phone_number="0000000000",  # Default phone number
                customer_number=f"AUTO{Customer.objects.count() + 1:04d}",
            )
            self.stdout.write(
                self.style.SUCCESS(f"Auto-created customer: {customer_name}")
            )
            return customer
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to auto-create customer '{customer_name}': {str(e)}"
                )
            )
            return None

    def _print_summary(self, created_count, existing_count, error_count):
        """Print execution summary"""
        self.stdout.write(
            self.style.SUCCESS(
                f"\nConversion Rate data initialization complete!\n"
                f"Created: {created_count} new records\n"
                f"Existing: {existing_count} records already present\n"
                f"Errors: {error_count} records skipped due to errors"
            )
        )

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nNote: {error_count} records had errors. Please ensure:\n"
                    f"1. All dependency data is loaded\n"
                    f"2. CSV format matches expected columns\n"
                    f"3. All referenced entities exist in the database"
                )
            )
