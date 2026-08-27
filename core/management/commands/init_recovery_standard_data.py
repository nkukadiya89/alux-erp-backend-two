import csv
import os
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from melting_furnace.models import FurnaceType, MaterialType, RecoveryStandard

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize master data for RecoveryStandard from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/recovery_standard.csv",
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
                self.style.WARNING(
                    f"Some dependencies might be missing: {missing_dependencies}\n"
                    "Continuing with available data..."
                )
            )

        self._process_recovery_standards(csv_file_path)

    def _initialize_dependencies(self):
        """Initialize all required dependency commands"""
        dependency_commands = [
            ("init_furnace_type_data", "Furnace Type data"),
            ("init_material_types", "Material Type data"),
        ]

        self.stdout.write(self.style.WARNING("Initializing dependencies..."))

        for command_name, description in dependency_commands:
            try:
                self.stdout.write(f"  - Initializing {description}...", ending="")
                call_command(command_name, verbosity=0)
                self.stdout.write(self.style.SUCCESS(" ✓"))
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f" ⚠ (may already exist or command not found)")
                )

    def _check_missing_dependencies(self, csv_file_path):
        """Check which required dependencies are missing from the database"""
        missing = {"furnace_types": [], "material_types": []}

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                unique_furnace_types = set()
                unique_material_codes = set()

                for row in reader:
                    ft = (row.get("furnace_type") or "").strip()
                    if ft:
                        unique_furnace_types.add(ft)
                    code = (
                        row.get("material_type_code") or row.get("material_type") or ""
                    ).strip()
                    if code:
                        unique_material_codes.add(code)

                existing_furnace = set(
                    FurnaceType.objects.filter(
                        name__in=unique_furnace_types
                    ).values_list("name", flat=True)
                )
                missing["furnace_types"] = list(unique_furnace_types - existing_furnace)

                existing_codes = set(
                    MaterialType.objects.filter(
                        code__in=unique_material_codes
                    ).values_list("code", flat=True)
                )
                missing["material_types"] = list(unique_material_codes - existing_codes)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking dependencies: {e}"))

        return {k: v for k, v in missing.items() if v}

    def _process_recovery_standards(self, csv_file_path):
        """Process the CSV file and create RecoveryStandard records. Uses material_type_code
        for MaterialType lookup and get_or_create on (furnace_type, material_type, remarks)
        for idempotency. condition -> remarks, is_active -> status.
        """
        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                created_count = 0
                updated_count = 0
                error_count = 0
                default_user = User.objects.filter(is_superuser=True).first()

                for row_num, row in enumerate(reader, start=1):
                    try:
                        material_type_code = (
                            row.get("material_type_code")
                            or row.get("material_type")
                            or ""
                        ).strip()
                        furnace_type_name = (row.get("furnace_type") or "").strip()
                        min_recovery = (row.get("min_recovery") or "").strip()
                        max_recovery = (row.get("max_recovery") or "").strip()
                        standard_loss = (row.get("standard_loss") or "").strip()
                        condition = (row.get("condition") or "").strip()
                        is_active_raw = (row.get("is_active") or "True").strip().lower()
                        is_active = is_active_raw in ("true", "1", "yes", "y")

                        if not all(
                            [
                                material_type_code,
                                furnace_type_name,
                                min_recovery,
                                max_recovery,
                                standard_loss,
                            ]
                        ):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Missing required fields "
                                    "(material_type_code, furnace_type, min_recovery, max_recovery, standard_loss)"
                                )
                            )
                            error_count += 1
                            continue

                        try:
                            min_recovery_val = Decimal(str(min_recovery))
                            max_recovery_val = Decimal(str(max_recovery))
                            standard_loss_val = Decimal(str(standard_loss))
                        except (ValueError, TypeError):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Invalid numeric values for recovery/loss"
                                )
                            )
                            error_count += 1
                            continue

                        furnace_type = FurnaceType.objects.filter(
                            name__iexact=furnace_type_name
                        ).first()
                        if not furnace_type:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Furnace Type not found: {furnace_type_name}"
                                )
                            )
                            error_count += 1
                            continue

                        material_type_obj = MaterialType.objects.filter(
                            code__iexact=material_type_code
                        ).first()
                        if not material_type_obj:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_num}: Material Type not found for code: {material_type_code}"
                                )
                            )
                            error_count += 1
                            continue

                        status = "Active" if is_active else "Inactive"
                        remarks = (
                            (row.get("remarks") or "").strip() or condition or None
                        )

                        recovery_data = {
                            "furnace_type": furnace_type,
                            "material_type": material_type_obj,
                            "min_recovery": min_recovery_val,
                            "max_recovery": max_recovery_val,
                            "standard_loss": standard_loss_val,
                            "status": status,
                            "remarks": remarks,
                            "created_by": default_user,
                        }

                        effective_from = (row.get("effective_from") or "").strip()
                        if effective_from:
                            try:
                                recovery_data["effective_from"] = datetime.strptime(
                                    effective_from, "%Y-%m-%d"
                                ).date()
                            except ValueError:
                                pass

                        unique_fields = {
                            "furnace_type": furnace_type,
                            "material_type": material_type_obj,
                            "remarks": recovery_data["remarks"],
                        }
                        recovery_standard, created = (
                            RecoveryStandard.objects.get_or_create(
                                **unique_fields, defaults=recovery_data
                            )
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created: {furnace_type_name} / {material_type_obj.code} "
                                    f"({recovery_data['remarks'] or 'default'})"
                                )
                            )
                        else:
                            for key, value in recovery_data.items():
                                if key != "created_by":
                                    setattr(recovery_standard, key, value)
                            recovery_standard.updated_by = default_user
                            recovery_standard.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Updated: {furnace_type_name} / {material_type_obj.code} "
                                    f"({recovery_data['remarks'] or 'default'})"
                                )
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: {row.get('furnace_type', '?')}: {e}"
                            )
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nRecoveryStandard init complete. "
                        f"Created: {created_count}, Updated: {updated_count}, Errors: {error_count}"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
