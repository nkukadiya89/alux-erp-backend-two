import csv
import os
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from common.models import UOM, ItemCategory
from product.models import Item, ItemType, MaterialCenter, ValuationMethod


class Command(BaseCommand):
    help = "Initialize all Item master data including prerequisites"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/item_data.csv",
            help="Path to CSV file (relative to project root)",
        )
        parser.add_argument(
            "--skip-prerequisites",
            action="store_true",
            help="Skip loading prerequisite data",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        skip_prerequisites = options.get("skip_prerequisites", False)

        if not skip_prerequisites:
            self.stdout.write(
                self.style.SUCCESS("=== Loading Prerequisites for Item Master ===")
            )
            self._load_prerequisites()

        self.stdout.write(self.style.SUCCESS("=== Loading Item Master Data ==="))

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
                error_count = 0

                for row in reader:
                    item_code = row.get("item_code", "").strip()
                    item_name = row.get("item_name", "").strip()

                    if not item_code or not item_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row with missing item_code or item_name: {row}"
                            )
                        )
                        error_count += 1
                        continue

                    # Prepare item data with foreign key lookups
                    item_data = self._prepare_item_data(row)

                    if item_data is None:
                        error_count += 1
                        continue

                    # Never set updated_at/created_at on create (BaseModel leaves updated_at null)
                    item_data.pop("updated_at", None)
                    item_data.pop("created_at", None)

                    # Create or get existing item
                    try:
                        obj, created = Item.objects.get_or_create(
                            item_code=item_code,
                            defaults=item_data,
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created Item: {item_code} - {item_name}"
                                )
                            )
                        else:
                            existing_count += 1
                            self.stdout.write(
                                self.style.WARNING(f"Item already exists: {item_code}")
                            )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error creating item {item_code}: {str(e)}"
                            )
                        )
                        error_count += 1
                        continue

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n{'='*60}\n"
                        f"ITEM DATA INITIALIZATION COMPLETE!\n"
                        f"{'='*60}\n"
                        f"Created: {created_count} new records\n"
                        f"Existing: {existing_count} records already present\n"
                        f"Errors: {error_count} records skipped due to errors\n"
                        f"{'='*60}"
                    )
                )

                if error_count > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"\nNote: {error_count} records had errors. "
                            f"This might be due to missing prerequisite data."
                        )
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def _load_prerequisites(self):
        """Load all prerequisite master data"""
        prerequisites = [
            ("UOM", self._init_uom_data),
            ("ItemCategory", self._init_item_category_data),
            ("ItemType/ValuationMethod/MaterialCenter", self._init_item_master_basics),
        ]

        for desc, func in prerequisites:
            try:
                self.stdout.write(f"\n--- Loading {desc} ---")
                func()
                self.stdout.write(self.style.SUCCESS(f"✓ {desc} loaded successfully"))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to load {desc}: {str(e)}")
                )

    def _init_uom_data(self):
        """Initialize UOM data"""
        uom_data = [
            ("KG", "Kilogram", "WEIGHT", True),
            ("MT", "Metric Ton", "WEIGHT", True),
            ("PCS", "Pieces", "COUNT", False),
            ("MTR", "Meter", "LENGTH", True),
            ("MM", "Millimeter", "LENGTH", True),
            ("CM", "Centimeter", "LENGTH", True),
            ("LTR", "Liter", "VOLUME", True),
            ("SQM", "Square Meter", "AREA", True),
            ("TON", "Ton", "WEIGHT", True),
            ("GM", "Gram", "WEIGHT", True),
        ]

        for code, name, uom_type, decimal_allowed in uom_data:
            UOM.objects.get_or_create(
                uom_code=code,
                defaults={
                    "uom_name": name,
                    "uom_type": uom_type,
                    "decimal_allowed": decimal_allowed,
                    "is_active": True,
                },
            )

    def _init_item_category_data(self):
        """Initialize ItemCategory data"""
        categories = [
            (
                "RAW",
                "Raw Materials",
                "RAW",
                "Raw aluminum materials including billets and ingots",
            ),
            ("FG", "Finished Goods", "FG", "Finished aluminum profiles and products"),
            (
                "CONSUMABLE",
                "Consumables",
                "CONSUMABLE",
                "Consumable materials for production",
            ),
            ("SEMI", "Semi-Finished", "SEMI", "Semi-finished aluminum products"),
            (
                "SPARE",
                "Spare Parts",
                "SPARE",
                "Spare parts for machinery and equipment",
            ),
            ("SCRAP", "Scrap Materials", "SCRAP", "Scrap aluminum for recycling"),
            ("TOOLING", "Tooling", "TOOLING", "Dies and tooling equipment"),
        ]

        for code, name, item_type, desc in categories:
            ItemCategory.objects.get_or_create(
                category_code=code,
                defaults={
                    "category_name": name,
                    "allowed_item_type": item_type,
                    "description": desc,
                    "status": "Active",
                    "is_archived": False,
                },
            )

    def _init_item_master_basics(self):
        """Initialize ItemType, ValuationMethod, and MaterialCenter"""
        # ItemType values
        item_types = ["BILLET", "PROFILE", "INGOT", "SCRAP", "POWDER", "DIE"]
        for name in item_types:
            ItemType.objects.get_or_create(name=name)

        # ValuationMethod values
        valuation_methods = ["FIFO", "AVG", "LIFO"]
        for name in valuation_methods:
            ValuationMethod.objects.get_or_create(name=name)

        # MaterialCenter values
        material_centers = ["STORE", "EXTRUSION", "ANODIZING", "POWDER", "PACKING"]
        for name in material_centers:
            MaterialCenter.objects.get_or_create(name=name)

    def _prepare_item_data(self, row):
        """Prepare item data with proper foreign key lookups and type conversions"""
        try:
            item_data = {
                "item_name": row.get("item_name", "").strip(),
            }

            # ItemType lookup
            item_type_name = row.get("item_type_name", "").strip()
            if item_type_name:
                try:
                    item_data["item_type"] = ItemType.objects.get(name=item_type_name)
                except ItemType.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"ItemType '{item_type_name}' not found for item {row.get('item_code')}"
                        )
                    )
                    return None

            # ItemCategory lookup
            category_code = row.get("category_code", "").strip()
            if category_code:
                try:
                    item_data["category"] = ItemCategory.objects.get(
                        category_code=category_code, is_archived=False
                    )
                except ItemCategory.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"ItemCategory '{category_code}' not found for item {row.get('item_code')}"
                        )
                    )
                    return None
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Category code is required for item {row.get('item_code')}"
                    )
                )
                return None

            # UOM lookup (required)
            uom_code = row.get("uom_code", "").strip()
            if uom_code:
                try:
                    item_data["uom"] = UOM.objects.get(uom_code=uom_code, deleted=False)
                except UOM.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"UOM '{uom_code}' not found for item {row.get('item_code')}"
                        )
                    )
                    return None
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"UOM code is required for item {row.get('item_code')}"
                    )
                )
                return None

            # Secondary UOM lookup (optional)
            secondary_uom_code = row.get("secondary_uom_code", "").strip()
            if secondary_uom_code:
                try:
                    item_data["secondary_uom"] = UOM.objects.get(
                        uom_code=secondary_uom_code, deleted=False
                    )
                except UOM.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Secondary UOM '{secondary_uom_code}' not found for item {row.get('item_code')}. Skipping secondary UOM."
                        )
                    )

            # ValuationMethod lookup
            valuation_method_name = row.get("valuation_method_name", "").strip()
            if valuation_method_name:
                try:
                    item_data["valuation_method"] = ValuationMethod.objects.get(
                        name=valuation_method_name
                    )
                except ValuationMethod.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"ValuationMethod '{valuation_method_name}' not found for item {row.get('item_code')}. Skipping valuation method."
                        )
                    )

            # MaterialCenter lookup
            material_center_name = row.get("material_center_name", "").strip()
            if material_center_name:
                try:
                    item_data["material_center"] = MaterialCenter.objects.get(
                        name=material_center_name
                    )
                except MaterialCenter.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"MaterialCenter '{material_center_name}' not found for item {row.get('item_code')}. Skipping material center."
                        )
                    )

            # Numeric fields with proper conversion
            numeric_fields = {
                "conversion_factor": "conversion_factor",
                "reorder_level": "reorder_level",
                "gst_rate": "gst_rate",
                "net_weight": "net_weight",
                "purchase_rate": "purchase_rate",
                "sale_rate": "sale_rate",
                "minimum_stock": "minimum_stock",
                "maximum_stock": "maximum_stock",
                "reorder_qty": "reorder_qty",
            }

            for csv_field, model_field in numeric_fields.items():
                value = row.get(csv_field, "").strip()
                if value:
                    try:
                        item_data[model_field] = Decimal(value)
                    except (ValueError, TypeError):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Invalid {csv_field} value '{value}' for item {row.get('item_code')}. Using default."
                            )
                        )

            # Integer fields
            integer_fields = {
                "making_time_minutes": "making_time_minutes",
                "lead_time_days": "lead_time_days",
            }

            for csv_field, model_field in integer_fields.items():
                value = row.get(csv_field, "").strip()
                if value:
                    try:
                        item_data[model_field] = int(value)
                    except (ValueError, TypeError):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Invalid {csv_field} value '{value}' for item {row.get('item_code')}. Using default."
                            )
                        )

            # Boolean fields
            boolean_fields = {
                "heat_tracking": "heat_tracking",
                "bom_required": "bom_required",
                "batch_managed": "batch_managed",
                "grn_required": "grn_required",
            }

            for csv_field, model_field in boolean_fields.items():
                value = row.get(csv_field, "").strip().lower()
                if value in ("true", "1", "yes"):
                    item_data[model_field] = True
                elif value in ("false", "0", "no"):
                    item_data[model_field] = False

            # String fields
            string_fields = {
                "alloy_code": "alloy_code",
                "hsn_code": "hsn_code",
                "base_unit": "base_unit",
            }

            for csv_field, model_field in string_fields.items():
                value = row.get(csv_field, "").strip()
                if value:
                    item_data[model_field] = value

            return item_data

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error preparing data for item {row.get('item_code')}: {str(e)}"
                )
            )
            return None
