import csv
import os
from datetime import datetime
from decimal import Decimal
from os import path

from decouple import config
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from aging.models import AgingCycle
from common.models import (
    Country,
    Currency,
    Department,
    FinancialYearModel,
    GstType,
    ItemCategory,
    Plant,
    SectionType,
    StoreType,
    YieldUnit,
)
from die.models import Die, DieCategory, DieGroup
from material.models import Material
from product.models import Alloy, Temper
from transporter.models import Transporter
from user.models import CustomGroup, User
from vehicle_master.models import VehicleMaster
from vehicle_type.models import VehicleType


class Command(BaseCommand):
    help = "Initialize all master data in proper dependency order"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-permissions",
            action="store_true",
            help="Skip creating Super Admin permissions",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )
        parser.add_argument(
            "--skip-conversion-rate",
            action="store_true",
            help="Skip conversion rate data initialization",
        )

    def load_financial_data(self):
        self.stdout.write("Loading Financial Year Data.......")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "financial.csv"
        )

        with open(file_path, "r") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")

            FinancialYearModel.objects.bulk_create(
                [
                    FinancialYearModel(
                        f_id=0,
                        financial_year=row["financial_year"],
                        start_date=row["start_date"],
                        end_date=row["end_date"],
                        current=row["current"],
                        default=row["default"],
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Financial data Uploaded SuccessFully..")

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)
        skip_permissions = options.get("skip_permissions", False)
        skip_conversion_rate = options.get("skip_conversion_rate", False)

        self.stdout.write(
            self.style.SUCCESS("Starting initialization of all master data...")
        )

        commands_sequence = [
            ("init_packing_mode_data", "Packing Mode"),
            ("init_uom_data", "Unit of Measurement"),
            ("init_yield_unit_data", "Yield Unit"),
            ("init_jobworktype_data", "Job Work Type"),
            ("init_customer_type_data", "Customer Type"),
            ("init_alloy_data", "Alloy"),
            ("init_section_type_data", "Section Type"),
            # Level 2: Dependent on Level 1
            ("init_temper_data", "Temper"),  # depends on section_type, uom, yield_unit
            # Level 3: Plant hierarchy (plant_type -> plant -> department)
            ("init_plant_type_data", "Plant Type"),
            ("init_plant_type_capability", "Plant Type Capability"),
            ("init_plant_data", "Plant"),  # depends on plant_type
            ("init_plant_capability", "Plant Capability"),  # depends on plant
            ("init_department_data", "Department"),  # depends on plant
            ("init_inspection_type_data", "Inspection Type"),  # optional plant
            ("init_storetype_data", "Store Type"),  # Store types for stores
            ("init_store_data", "Store"),
            ("init_customer_dummy_data", "Customer"),
            ("init_vendor_data", "Vendor"),
            ("init_die_group_data", "Die Group"),
            ("init_die_category_data", "Die Category"),
            ("init_die_sub_category_data", "Die Sub Category"),
            ("init_die_size_data", "Die Size"),
            ("init_die_press_data", "Die Press"),
            ("init_die_data", "Die"),
            ("init_item_category_data", "Item Category"),
            ("init_item_master_data", "Item Master"),
            ("init_fuel_type_data", "Fuel Type"),
            ("init_furnace_type_data", "Furnace Type"),
            ("init_additive_category_data", "Additive Category"),
            ("init_additive_master_data", "Additive Master"),
            ("init_furnace_data", "Furnace"),
            ("init_material_types", "Material Type"),
            ("init_recovery_standard_data", "Recovery Standard"),
        ]

        # Load financial data first
        self.load_financial_data()

        if not skip_conversion_rate:
            commands_sequence.append(("init_conversion_rate_data", "Conversion Rate"))

        total_commands = len(commands_sequence)
        successful_commands = 0
        failed_commands = []

        for i, (command_name, description) in enumerate(commands_sequence, 1):
            try:
                if verbose:
                    self.stdout.write(
                        f"\n[{i}/{total_commands}] Executing: {command_name}"
                    )

                self.stdout.write(f"Initializing {description}...", ending="")

                call_command(command_name, verbosity=0 if not verbose else 2)

                self.stdout.write(self.style.SUCCESS(" ✓"))
                successful_commands += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(" ✗"))
                error_msg = f"{command_name}: {str(e)}"
                failed_commands.append(error_msg)

                if verbose:
                    self.stdout.write(self.style.ERROR(f"  Error: {str(e)}"))
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  Failed to initialize {description}")
                    )

        if not skip_permissions:
            try:
                self.stdout.write("\nCreating Super Admin permissions...", ending="")
                self.create_super_admin_permissions()
                self.stdout.write(self.style.SUCCESS(" ✓"))
                successful_commands += 1
            except Exception as e:
                failed_commands.append(f"Super Admin permissions: {str(e)}")
                self.stdout.write(self.style.ERROR(" ✗"))
                if verbose:
                    self.stdout.write(self.style.ERROR(f"  Error: {str(e)}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"Initialization Summary: {successful_commands} successful, "
                f"{len(failed_commands)} failed"
            )
        )

        if failed_commands:
            self.stdout.write("\nFailed commands:")
            for error in failed_commands:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            self.stdout.write(
                self.style.WARNING(
                    "\nSome commands failed. You may need to run them individually "
                    "or check the error messages above."
                )
            )

            if any("conversion_rate" in error.lower() for error in failed_commands):
                self.stdout.write(
                    self.style.WARNING(
                        "\nConversion rate initialization failed due to missing dependencies.\n"
                        "You can:\n"
                        "1. Run with --skip-conversion-rate to skip this step\n"
                        "2. Ensure your CSV files have matching data\n"
                        "3. Run individual commands manually in correct order"
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nAll commands executed successfully! 🎉")
            )

    def create_super_admin_permissions(self):
        """Create Super Admin user group with all necessary permissions"""
        from django.contrib.auth.models import Permission

        from user.models import CustomGroup

        self.create_superuser()
        self.create_custom_groups()

        all_permissions = Permission.objects.all()

        super_admin_group = CustomGroup.objects.get(name="Super Admin")
        super_admin_group.permissions.set(all_permissions)
        super_admin_group.save()

        return super_admin_group

    def create_superuser(self):
        """Create superuser"""

        if not len(User.objects.filter(is_superuser=True)) > 0:
            email = config("INIT_EMAIL")
            password = config("ADMIN_PASSWORD")
            user = User.objects.create(email=email, username="Alux_admin")
            user.set_password(password)  # type: ignore
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.first_name = "Alux"
            user.last_name = "Admin"
            user.status = "active"
            user.save()
            group, created = CustomGroup.objects.get_or_create(name="Super Admin")
            group.user_set.add(user)
            self.stdout.write("Super User Created!.......")
            return user

    def create_custom_groups(self):
        self.stdout.write("Creating Groups.......")
        super_admin_group, _ = CustomGroup.objects.get_or_create(name="Super Admin")
        sales_executive_assistant_group, _ = CustomGroup.objects.get_or_create(
            name="Sales Executive Assistant"
        )
        sales_executive_group, _ = CustomGroup.objects.get_or_create(
            name="Sales Executive"
        )
        purchaser_group, _ = CustomGroup.objects.get_or_create(name="Purchaser")

        sales_executive_permissions = [
            "aging|Can change aging cycle",
            "aging|Can delete aging cycle",
            "aging|Can view aging cycle",
            "bloster|Can add bloster master",
            "bloster|Can change bloster master",
            "bloster|Can view bloster master",
            "bundle_inward|Can add bundle inward",
            "bundle_inward|Can change bundle inward",
            "bundle_inward|Can print bundle inward",
            "bundle_inward|Can print current stock",
            "bundle_inward|Can print packing datewise report",
            "bundle_inward|Can print packing report",
            "bundle_inward|Can view bundle inward",
            "bundle_inward|Can add excess stock",
            "bundle_inward|Can change excess stock",
            "bundle_inward|Can print excess stock",
            "bundle_inward|Can view excess stock",
            "bundle_outward|Can add bundle outward",
            "bundle_outward|Can change bundle outward",
            "bundle_outward|Can print bundle outward",
            "bundle_outward|Can print dispatch report",
            "bundle_outward|Can view bundle outward",
            "bundle_outward|Can add bundle outward inward",
            "bundle_outward|Can change bundle outward inward",
            "bundle_outward|Can view bundle outward inward",
            "bundle_outward|Can add bundle outward outward",
            "bundle_outward|Can change bundle outward outward",
            "bundle_outward|Can view bundle outward outward",
            "common|Can add Department",
            "common|Can change Department",
            "common|Can view Department",
            "common|Can add Item Category",
            "common|Can change Item Category",
            "common|Can view Item Category",
            "common|Can add job work type",
            "common|Can change job work type",
            "common|Can view job work type",
            "common|Can add packing mode",
            "common|Can change packing mode",
            "common|Can view packing mode",
            "common|Can add plant",
            "common|Can change plant",
            "common|Can view plant",
            "common|Can add Plant Capability",
            "common|Can change Plant Capability",
            "common|Can view Plant Capability",
            "common|Can add plant type",
            "common|Can change plant type",
            "common|Can view plant type",
            "plant_type_capability|Can add Plant Type Capability",
            "plant_type_capability|Can change Plant Type Capability",
            "plant_type_capability|Can view Plant Type Capability",
            "common|Can add Section Type",
            "common|Can change Section Type",
            "common|Can view Section Type",
            "common|Can add uom",
            "common|Can change uom",
            "common|Can view uom",
            "common|Can add yield unit",
            "common|Can change yield unit",
            "common|Can view yield unit",
            "customer|Can add customer",
            "customer|Can change customer",
            "customer|Can print customer workorder report",
            "customer|Can view customer",
            "customer|Can add customer type",
            "customer|Can change customer type",
            "customer|Can view customer type",
            "die|Can add conversion rate",
            "die|Can change conversion rate",
            "die|Can view conversion rate",
            "die|Can add die",
            "die|Can change die",
            "die|Can print profile",
            "die|Can print profile workorder report",
            "die|Can view die",
            "die|Can add die category",
            "die|Can change die category",
            "die|Can view die category",
            "die|Can add die group",
            "die|Can change die group",
            "die|Can view die group",
            "die|Can add die press",
            "die|Can change die press",
            "die|Can view die press",
            "die|Can add die size",
            "die|Can change die size",
            "die|Can view die size",
            "die|Can add die sub category",
            "die|Can change die sub category",
            "die|Can view die sub category",
            "die|Can add die tool",
            "die|Can change die tool",
            "die|Can view die tool",
            "die|Can add die type",
            "die|Can change die type",
            "die|Can view die type",
            "die|Can add section ballon dimensions",
            "die|Can change section ballon dimensions",
            "die|Can view section ballon dimensions",
            "die_quotation|Can add die quotation",
            "die_quotation|Can change die quotation",
            "die_quotation|Can print die quotation",
            "die_quotation|Can view die quotation",
            "inquiry|Can add inquiry",
            "inquiry|Can change inquiry",
            "inquiry|Can print inquiry",
            "inquiry|Can view inquiry",
            "inquiry_quotation|Can add inquiry quotation",
            "inquiry_quotation|Can change inquiry quotation",
            "inquiry_quotation|Can print inquiry quotation",
            "inquiry_quotation|Can view inquiry quotation",
            "inquiry_salesorder|Can add inquiry sales order",
            "inquiry_salesorder|Can change inquiry sales order",
            "inquiry_salesorder|Can print Inquiry Sales Order",
            "inquiry_salesorder|Can view inquiry sales order",
            "msg_logger|Can add log activity",
            "msg_logger|Can change log activity",
            "msg_logger|Can view log activity",
            "nalco|Can add nalco master",
            "nalco|Can change nalco master",
            "nalco|Can view nalco master",
            "planning|Can add planning",
            "planning|Can change planning",
            "planning|Can view planning",
            "product|Can add alloy",
            "product|Can change alloy",
            "product|Can view alloy",
            "product|Can add temper",
            "product|Can change temper",
            "product|Can view temper",
            "production|Can add production",
            "production|Can change production",
            "production|Can view production",
            "proforma|Can add proforma",
            "proforma|Can change proforma",
            "proforma|Can print proforma copy",
            "proforma|Can print die quotation",
            "proforma|Can view proforma",
            "quotation|Can add quotation",
            "quotation|Can change quotation",
            "quotation|Can print quotation",
            "quotation|Can view quotation",
            "user|Can add custom group",
            "user|Can change custom group",
            "user|Can view custom group",
            "user|Can add user",
            "user|Can change user",
            "user|Can view user",
            "vendor|Can add vendor",
            "vendor|Can change vendor",
            "vendor|Can view vendor",
            "warehouse|Can add warehouse",
            "warehouse|Can change warehouse",
            "warehouse|Can print warehouse bundle outward",
            "warehouse|Can print warehouse current stock",
            "warehouse|Can view warehouse",
            "warehouse|Can add warehouse bundle inward",
            "warehouse|Can change warehouse bundle inward",
            "warehouse|Can delete warehouse bundle inward",
            "warehouse|Can view warehouse bundle inward",
            "warehouse|Can add warehouse bundle outward",
            "warehouse|Can change warehouse bundle outward",
            "warehouse|Can delete warehouse bundle outward",
            "warehouse|Can view warehouse bundle outward",
            "workorder|Can add work order",
            "workorder|Can change profile over weight",
            "workorder|Can change work order",
            "workorder|Can print account sales copy",
            "workorder|Can print packing copy",
            "workorder|Can print production copy",
            "workorder|Can print workorder copy",
            "workorder|Can print workorder report",
            "workorder|Can view work order",
        ]

        sales_executive_assistant_permissions = [
            "aging|Can change aging cycle",
            "aging|Can delete aging cycle",
            "aging|Can view aging cycle",
            "bloster|Can add bloster master",
            "bloster|Can change bloster master",
            "bloster|Can delete bloster master",
            "bloster|Can download bolster Excel",
            "bloster|Can download bolster PDF",
            "bloster|Can view bloster master",
            "bundle_inward|Can add bundle inward",
            "bundle_inward|Can change bundle inward",
            "bundle_inward|Can delete bundle inward",
            "bundle_inward|Can download bundle inward Excel",
            "bundle_inward|Can download current stock Excel",
            "bundle_inward|Can download packing datewise report Excel",
            "bundle_inward|Can download packing report Excel",
            "bundle_inward|Can print bundle inward",
            "bundle_inward|Can print current stock",
            "bundle_inward|Can print packing datewise report",
            "bundle_inward|Can print packing report",
            "bundle_inward|Can view bundle inward",
            "excess_stock|Can add excess stock",
            "excess_stock|Can change excess stock",
            "excess_stock|Can delete excess stock",
            "excess_stock|Can download excess stock Excel",
            "excess_stock|Can print excess stock",
            "excess_stock|Can view excess stock",
            "bundle_outward|Can add bundle outward",
            "bundle_outward|Can change bundle outward",
            "bundle_outward|Can delete bundle outward",
            "bundle_outward|Can download bundle outward Excel",
            "bundle_outward|Can download dispatch report Excel",
            "bundle_outward|Can print bundle outward",
            "bundle_outward|Can print dispatch report",
            "bundle_outward|Can view bundle outward",
            "bundle_outward_inward|Can add bundle outward inward",
            "bundle_outward_inward|Can change bundle outward inward",
            "bundle_outward_inward|Can delete bundle outward inward",
            "bundle_outward_inward|Can view bundle outward inward",
            "bundle_outward|Can add bundle outward outward",
            "bundle_outward|Can change bundle outward outward",
            "bundle_outward|Can view bundle outward outward",
            "bundle_outward|Can delete bundle outward outward",
            "common|Can add Department",
            "common|Can change Department",
            "common|Can view Department",
            "common|Can download department Excel",
            "common|Can download department PDF",
            "common|Can add Item Category",
            "common|Can change Item Category",
            "common|Can delete Item Category",
            "common|Can view Item Category",
            "common|Can download item category Excel",
            "common|Can download item category PDF",
            "common|Can add job work type",
            "common|Can change job work type",
            "common|Can delete job work type",
            "common|Can view job work type",
            "common|Can add packing mode",
            "common|Can change packing mode",
            "common|Can delete packing mode",
            "common|Can view packing mode",
            "common|Can download packing_mode Excel",
            "common|Can download packing_mode PDF",
            "common|Can add plant",
            "common|Can change plant",
            "common|Can delete plant",
            "common|Can view plant",
            "common|Can add Plant Capability",
            "common|Can change Plant Capability",
            "common|Can delete Plant Capability",
            "common|Can download plant type Excel",
            "common|Can download plant type PDF",
            "common|Can view Plant Capability",
            "common|Can add plant type",
            "common|Can change plant type",
            "common|Can delete plant type",
            "common|Can view plant type",
            "common|Can add Section Type",
            "common|Can change Section Type",
            "common|Can delete Section Type",
            "common|Can view Section Type",
            "common|Can add uom",
            "common|Can change uom",
            "common|Can delete uom",
            "common|Can view uom",
            "common|Can add yield unit",
            "common|Can change yield unit",
            "common|Can delete yield unit",
            "common|Can view yield unit",
            "customer|Can add customer",
            "customer|Can change customer",
            "customer|Can delete customer",
            "customer|Can download customer Excel",
            "customer|Can download customer PDF",
            "customer|Can print customer workorder report",
            "customer|Can view customer",
            "customer|Can add customer type",
            "customer|Can change customer type",
            "customer|Can delete customer type",
            "customer|Can view customer type",
            "customer|Can download customer type Excel",
            "customer|Can download customer type PDF",
            "die|Can add die",
            "die|Can change die",
            "die|Can delete die",
            "die|Can download profile Excel",
            "die|Can download profile PDF",
            "die|Can print profile",
            "die|Can print profile workorder report",
            "die|Can view die",
            "die_quotation|Can add die quotation",
            "die_quotation|Can change die quotation",
            "die_quotation|Can delete die quotation",
            "die_quotation|Can download die quotation Excel",
            "die_quotation|Can print die quotation",
            "die_quotation|Can view die quotation",
            "inquiry|Can add inquiry",
            "inquiry|Can change inquiry",
            "inquiry|Can delete inquiry",
            "inquiry|Can download inquiry Excel",
            "inquiry|Can download inquiry PDF",
            "inquiry|Can print inquiry",
            "inquiry|Can view inquiry",
            "inquiry_quotation|Can add inquiry quotation",
            "inquiry_quotation|Can change inquiry quotation",
            "inquiry_quotation|Can delete inquiry quotation",
            "inquiry_quotation|Can download inquiry quotation Excel",
            "inquiry_quotation|Can download inquiry quotation PDF",
            "inquiry_quotation|Can print inquiry quotation",
            "inquiry_quotation|Can view inquiry quotation",
            "inquiry_sales_order|Can add inquiry sales order",
            "inquiry_sales_order|Can change inquiry sales order",
            "inquiry_sales_order|Can delete inquiry sales order",
            "inquiry_sales_order|Can download Inquiry Sales Order Excel",
            "inquiry_sales_order|Can download Inquiry Sales Order PDF",
            "inquiry_sales_order|Can print Inquiry Sales Order",
            "inquiry_sales_order|Can view inquiry sales order",
            "planning|Can add planning",
            "planning|Can change planning",
            "planning|Can delete planning",
            "planning|Can download planning Excel",
            "planning|Can download planning PDF",
            "planning|Can download planning priority Excel",
            "planning|Can download planning priority PDF",
            "planning|Can view planning",
            "proforma|Can add proforma",
            "proforma|Can change proforma",
            "proforma|Can delete proforma",
            "proforma|Can download proforma Excel",
            "proforma|Can print proforma copy",
            "proforma|Can print die quotation",
            "proforma|Can view proforma",
            "quotation|Can add quotation",
            "quotation|Can change quotation",
            "quotation|Can delete quotation",
            "quotation|Can download quotation Excel",
            "quotation|Can print quotation",
            "quotation|Can view quotation",
            "user|Can add user",
            "user|Can change user",
            "user|Can delete user",
            "user|Can download user Excel",
            "user|Can download user PDF",
            "user|Can view user",
            "user|Can add custom group",
            "user|Can change custom group",
            "user|Can delete custom group",
            "user|Can view custom group",
            "vendor|Can add vendor",
            "vendor|Can change vendor",
            "vendor|Can delete vendor",
            "vendor|Can download vendor Excel",
            "vendor|Can download vendor PDF",
            "vendor|Can view vendor",
            "warehouse|Can add warehouse",
            "warehouse|Can change warehouse",
            "warehouse|Can delete warehouse",
            "warehouse|Can download warehouse bundle outward Excel",
            "warehouse|Can download warehouse current stock Excel",
            "warehouse|Can print warehouse bundle outward",
            "warehouse|Can print warehouse current stock",
            "warehouse|Can view warehouse",
            "workorder|Can add work order",
            "workorder|Can change work order",
            "workorder|Can change profile over weight",
            "workorder|Can delete work order",
            "workorder|Can download workorder Excel",
            "workorder|Can download workorder report Excel",
            "workorder|Can print account sales copy",
            "workorder|Can print packing copy",
            "workorder|Can print production copy",
            "workorder|Can print workorder copy",
            "workorder|Can print workorder report",
            "workorder|Can view work order",
        ]

        self.assign_permissions(
            sales_executive_assistant_group, sales_executive_assistant_permissions
        )
        self.assign_permissions(sales_executive_group, sales_executive_permissions)

    def assign_permissions(self, group, permissions):
        for permission_name in permissions:
            try:
                app_label, codename = permission_name.split("|")
                permission_obj = Permission.objects.get(
                    content_type__app_label=app_label, name=codename
                )
                group.permissions.add(permission_obj)
                self.stdout.write(
                    f"Assigned {app_label and codename} permission to {group.name} group"
                )
            except Permission.DoesNotExist:
                self.stdout.write(
                    f"Permission {permission_name} does not exist. Skipping assignment to {group.name} group"
                )
            except Permission.MultipleObjectsReturned:
                self.stdout.write(
                    f"Multiple permissions with the name {permission_name} exist. Skipping assignment to {group.name} group"
                )
