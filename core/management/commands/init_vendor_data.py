import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from vendor.models import BankDetails, KeyPersons, Vendor


class Command(BaseCommand):
    help = "Initialize vendor data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/vendor_data.csv",
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
                updated_count = 0
                error_count = 0

                for row in reader:
                    try:
                        vendor_registered_name = row.get(
                            "vendor_registered_name", ""
                        ).strip()
                        person_name = row.get("person_name", "").strip()
                        email = row.get("email", "").strip()
                        phone = row.get("phone", "").strip()

                        if not vendor_registered_name or not person_name or not email:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Skipping row with missing required fields: {row}"
                                )
                            )
                            continue

                        # Check if vendor already exists
                        vendor, created = Vendor.objects.get_or_create(
                            email=email,
                            defaults={
                                "person_name": person_name,
                                "designation": row.get("designation", "").strip(),
                                "phone": phone,
                                "business_type": row.get(
                                    "business_type", "INDIAN"
                                ).strip(),
                                "vendor_registered_name": vendor_registered_name,
                                "vendor_trade_name": row.get(
                                    "vendor_trade_name", ""
                                ).strip(),
                                "gst_no": row.get("gst_no", "").strip(),
                                "pan_number": row.get("pan_number", "").strip(),
                                "code": row.get("code", "").strip(),
                                "fax_number": row.get("fax_number", "").strip(),
                                "website": row.get("website", "").strip() or None,
                                "is_active": row.get("is_active", "false").lower()
                                == "true",
                                "status": row.get("status", "pending").strip(),
                                "registered_business_address_building": row.get(
                                    "registered_business_address_building", ""
                                ).strip(),
                                "registered_business_address_area": row.get(
                                    "registered_business_address_area", ""
                                ).strip(),
                                "registered_business_address_landmark": row.get(
                                    "registered_business_address_landmark", ""
                                ).strip(),
                                "registered_business_address_pincode": row.get(
                                    "registered_business_address_pincode", ""
                                ).strip(),
                                "registered_business_address_state": row.get(
                                    "registered_business_address_state", ""
                                ).strip(),
                                "registered_business_address_city": row.get(
                                    "registered_business_address_city", ""
                                ).strip(),
                                "registered_business_address_country": row.get(
                                    "registered_business_address_country", ""
                                ).strip(),
                                "udyam_aadhaar_no": row.get(
                                    "udyam_aadhaar_no", ""
                                ).strip()
                                or None,
                            },
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"✓ Created vendor: {vendor_registered_name} ({email})"
                                )
                            )
                        else:
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠ Vendor already exists: {vendor_registered_name} ({email})"
                                )
                            )

                        # Create key person if provided
                        key_person_name = row.get("key_person_name", "").strip()
                        key_person_designation = row.get(
                            "key_person_designation", ""
                        ).strip()
                        key_person_email = row.get("key_person_email", "").strip()
                        key_person_contact = row.get("key_person_contact", "").strip()

                        if key_person_name:
                            key_person, kp_created = KeyPersons.objects.get_or_create(
                                vendor=vendor,
                                person_name=key_person_name,
                                defaults={
                                    "designation": key_person_designation,
                                    "email": key_person_email or None,
                                    "contact_number": key_person_contact,
                                },
                            )
                            if kp_created:
                                self.stdout.write(
                                    f"  ✓ Added key person: {key_person_name}"
                                )

                        # Create bank details if provided
                        bank_name = row.get("bank_name", "").strip()
                        bank_account_number = row.get("bank_account_number", "").strip()
                        bank_ifsc_code = row.get("bank_ifsc_code", "").strip()

                        if bank_name and bank_account_number:
                            bank_detail, bd_created = BankDetails.objects.get_or_create(
                                vendor=vendor,
                                bank_account_number=bank_account_number,
                                defaults={
                                    "bank_name": bank_name,
                                    "bank_ifsc_code": bank_ifsc_code,
                                    "branch_address": row.get(
                                        "branch_address", ""
                                    ).strip(),
                                    "bank_ad_code": row.get("bank_ad_code", "").strip()
                                    or None,
                                    "beneficiary_swift_code": row.get(
                                        "beneficiary_swift_code", ""
                                    ).strip()
                                    or None,
                                },
                            )
                            if bd_created:
                                self.stdout.write(
                                    f"  ✓ Added bank details: {bank_name}"
                                )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"✗ Error processing row {row}: {str(e)}")
                        )

                # Summary
                self.stdout.write("\n" + "=" * 50)
                self.stdout.write(self.style.SUCCESS(f"✅ SUMMARY:"))
                self.stdout.write(f"   • Created: {created_count} vendors")
                self.stdout.write(f"   • Already existed: {updated_count} vendors")
                self.stdout.write(f"   • Errors: {error_count} vendors")
                self.stdout.write("=" * 50)

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
