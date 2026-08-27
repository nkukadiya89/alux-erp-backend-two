"""
Item Master bulk importer
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from common.models import UOM, ItemCategory
from imports.services.base_importer import BaseImporter
from imports.utils import (
    excel_decimal,
    normalize_boolean,
    normalize_integer,
    normalize_string,
)
from imports.validators.field_validators import (
    ChoiceValidator,
    DecimalValidator,
    IntegerValidator,
    StringValidator,
    UniqueValidator,
)
from imports.validators.reference_validators import ForeignKeyValidator
from product.models import Item, ItemType, MaterialCenter, ValuationMethod

logger = logging.getLogger(__name__)


class ItemImporter(BaseImporter):
    """
    Bulk importer for Item Master module
    """

    MODULE_NAME = "Item"
    REQUIRED_COLUMNS = [
        "Item Code",
        "Item Name",
        "Item Type",
        "Category",
        "UOM",
        "BOM Required",
        "GRN Required",
    ]
    ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
    BATCH_SIZE = 500

    def __init__(self, file, user=None, dry_run: bool = False):
        super().__init__(file, user, dry_run)
        self.seen_item_codes = set()
        self.category_cache = {}
        self.uom_cache = {}
        self.item_type_cache = {}
        self.valuation_method_cache = {}
        self.material_center_cache = {}

    def get_field_mapping(self) -> Dict[str, str]:
        return {
            "Item Code": "item_code",
            "Item Name": "item_name",
            "Item Type": "item_type",
            "Category": "category",
            "UOM": "uom",
            "Alloy Code": "alloy_code",
            "Heat Tracking": "heat_tracking",
            "Reorder Level": "reorder_level",
            "Status": "status",
            "HSN Code": "hsn_code",
            "GST Rate": "gst_rate",
            "Base Unit": "base_unit",
            "Net Weight": "net_weight",
            "Purchase Rate": "purchase_rate",
            "Sale Rate": "sale_rate",
            "Valuation Method": "valuation_method",
            "Minimum Stock": "minimum_stock",
            "Maximum Stock": "maximum_stock",
            "Reorder Qty": "reorder_qty",
            "Making Time Minutes": "making_time_minutes",
            "Lead Time Days": "lead_time_days",
            "BOM Required": "bom_required",
            "Material Center": "material_center",
            "Batch Managed": "batch_managed",
            "GRN Required": "grn_required",
        }

    def get_validators(self) -> Dict[str, List]:
        return {
            "item_code": [
                UniqueValidator("item_code", self.seen_item_codes, required=True),
                StringValidator(
                    "item_code", max_length=100, required=True, pattern=r"^[A-Z0-9_-]+$"
                ),
            ],
            "item_name": [StringValidator("item_name", max_length=255, required=True)],
            "item_type": [
                ForeignKeyValidator(
                    "item_type",
                    ItemType,
                    lookup_field="name",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "category": [
                ForeignKeyValidator(
                    "category",
                    ItemCategory,
                    lookup_field="category_code",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "uom": [
                ForeignKeyValidator(
                    "uom",
                    UOM,
                    lookup_field="uom_code",
                    required=True,
                    case_sensitive=False,
                )
            ],
            "alloy_code": [
                StringValidator("alloy_code", max_length=50, required=False)
            ],
            "heat_tracking": [],
            "reorder_level": [
                DecimalValidator(
                    "reorder_level", max_digits=10, decimal_places=2, required=False
                )
            ],
            "status": [ChoiceValidator("status", Item.STATUS_CHOICES, required=False)],
            "hsn_code": [StringValidator("hsn_code", max_length=10, required=False)],
            "gst_rate": [
                DecimalValidator(
                    "gst_rate", max_digits=5, decimal_places=2, required=False
                )
            ],
            "base_unit": [StringValidator("base_unit", max_length=10, required=False)],
            "net_weight": [
                DecimalValidator(
                    "net_weight", max_digits=10, decimal_places=3, required=False
                )
            ],
            "purchase_rate": [
                DecimalValidator(
                    "purchase_rate", max_digits=12, decimal_places=2, required=False
                )
            ],
            "sale_rate": [
                DecimalValidator(
                    "sale_rate", max_digits=12, decimal_places=2, required=False
                )
            ],
            "valuation_method": [
                ForeignKeyValidator(
                    "valuation_method",
                    ValuationMethod,
                    lookup_field="name",
                    required=False,
                    case_sensitive=False,
                )
            ],
            "minimum_stock": [
                DecimalValidator(
                    "minimum_stock", max_digits=12, decimal_places=3, required=False
                )
            ],
            "maximum_stock": [
                DecimalValidator(
                    "maximum_stock", max_digits=12, decimal_places=3, required=False
                )
            ],
            "reorder_qty": [
                DecimalValidator(
                    "reorder_qty", max_digits=12, decimal_places=3, required=False
                )
            ],
            "making_time_minutes": [
                IntegerValidator("making_time_minutes", min_value=0, required=False)
            ],
            "lead_time_days": [
                IntegerValidator("lead_time_days", min_value=0, required=False)
            ],
            "bom_required": [],
            "material_center": [
                ForeignKeyValidator(
                    "material_center",
                    MaterialCenter,
                    lookup_field="name",
                    required=False,
                    case_sensitive=False,
                )
            ],
            "batch_managed": [],
            "grn_required": [],
        }

    def validate_row(self, row_data: Dict, row_number: int) -> bool:
        is_valid = super().validate_row(row_data, row_number)

        # Business rule: minimum_stock <= maximum_stock
        min_stock = row_data.get("minimum_stock")
        max_stock = row_data.get("maximum_stock")

        if min_stock is not None and max_stock is not None and min_stock > max_stock:
            self._add_row_error(
                row_number,
                [
                    {
                        "field": "minimum_stock",
                        "message": "Minimum stock cannot be greater than maximum stock",
                        "value": str(min_stock),
                    }
                ],
                row_data=row_data,
            )
            is_valid = False

        return is_valid

    def transform_row_data(self, row_data: Dict) -> Dict:
        field_mapping = self.get_field_mapping()
        transformed = {}

        # Case-insensitive column lookup
        row_data_lower = {k.strip().lower(): v for k, v in row_data.items()}

        for col_name, field_name in field_mapping.items():
            value = row_data.get(col_name)
            if value is None:
                lower_col = col_name.strip().lower()
                if lower_col in row_data_lower:
                    value = row_data_lower[lower_col]

            if field_name == "item_code":
                transformed[field_name] = (
                    normalize_string(value).upper() if value else None
                )
            elif field_name == "item_name":
                transformed[field_name] = normalize_string(value)
            elif field_name in [
                "item_type",
                "category",
                "uom",
                "valuation_method",
                "material_center",
            ]:
                transformed[field_name] = self._get_cached_fk(field_name, value)
            elif field_name in [
                "heat_tracking",
                "bom_required",
                "batch_managed",
                "grn_required",
            ]:
                # Boolean fields (Yes/No support)
                if isinstance(value, str):
                    val_lower = value.strip().lower()
                    if val_lower in ("yes", "y", "true", "1"):
                        transformed[field_name] = True
                    elif val_lower in ("no", "n", "false", "0"):
                        transformed[field_name] = False
                    else:
                        transformed[field_name] = normalize_boolean(value)
                else:
                    transformed[field_name] = (
                        normalize_boolean(value) if value is not None else None
                    )
            elif field_name == "status":
                # Handle Status column
                if value:
                    s = normalize_string(
                        value
                    ).title()  # Active / inactive → Active / Inactive
                    if s in ("Active", "Inactive"):
                        transformed[field_name] = s
                        transformed["is_active"] = s == "Active"
                    else:
                        logger.warning(
                            f"Invalid status value '{value}' in row - defaulting to Active"
                        )
                        transformed[field_name] = "Active"
                        transformed["is_active"] = True
                else:
                    # No Status → default
                    transformed[field_name] = "Active"
                    transformed["is_active"] = True
            elif field_name in [
                "gst_rate",
                "net_weight",
                "purchase_rate",
                "sale_rate",
                "minimum_stock",
                "maximum_stock",
                "reorder_qty",
                "reorder_level",
            ]:
                transformed[field_name] = excel_decimal(value)
            elif field_name in ["making_time_minutes", "lead_time_days"]:
                transformed[field_name] = normalize_integer(value) or 0
            else:
                transformed[field_name] = normalize_string(value)

        # Apply defaults for fields not set
        defaults = {
            "gst_rate": Decimal("0.00"),
            "net_weight": Decimal("0.000"),
            "purchase_rate": Decimal("0.00"),
            "minimum_stock": Decimal("0.000"),
            "maximum_stock": Decimal("0.000"),
            "reorder_qty": Decimal("0.000"),
            "making_time_minutes": 0,
            "lead_time_days": 0,
            "batch_managed": True,
            "grn_required": True,
            "bom_required": False,
            "base_unit": "KG",
            "heat_tracking": False,
        }
        for k, v in defaults.items():
            if k not in transformed or transformed[k] is None:
                transformed[k] = v

        # Audit fields
        transformed["created_by"] = self.user
        transformed["updated_by"] = self.user
        transformed["created_at"] = timezone.now()
        transformed["updated_at"] = timezone.now()
        transformed["deleted"] = False
        transformed["deleted_at"] = None
        transformed["deleted_by"] = None

        if "_row_number" in row_data:
            transformed["_row_number"] = row_data["_row_number"]
        transformed["_original_row_data"] = {
            k: v for k, v in row_data.items() if k != "_row_number"
        }

        return transformed

    def _get_cached_fk(self, field_name: str, value):
        if not value:
            return None
        normalized = normalize_string(value).upper()
        cache_map = {
            "item_type": (self.item_type_cache, ItemType, "name", None),
            "category": (
                self.category_cache,
                ItemCategory,
                "category_code",
                {"is_archived": False},
            ),
            "uom": (
                self.uom_cache,
                UOM,
                "uom_code",
                {"deleted": False, "is_active": True},
            ),
            "valuation_method": (
                self.valuation_method_cache,
                ValuationMethod,
                "name",
                None,
            ),
            "material_center": (
                self.material_center_cache,
                MaterialCenter,
                "name",
                None,
            ),
        }
        cache_tuple = cache_map.get(field_name)
        if not cache_tuple:
            return None
        cache, model, lookup, extra = cache_tuple
        key = normalized
        if key not in cache:
            try:
                filters = {f"{lookup}__iexact": key}
                if extra:
                    filters.update(extra)
                obj = model.objects.filter(**filters).first()
                cache[key] = obj
            except Exception as e:
                logger.error(f"FK lookup error {field_name} '{key}': {e}")
                cache[key] = None
        return cache.get(key)

    def _normalize_for_compare(self, field_name: str, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            v = value.strip()
            return v if v else None
        if isinstance(value, Decimal):
            return value.quantize(Decimal("1." + "0" * 12)) if value else None
        return value

    def _is_exact_duplicate(self, existing: Item, data: Dict) -> bool:
        compare_fields = [
            "item_code",
            "item_name",
            "item_type",
            "category",
            "uom",
            "alloy_code",
            "heat_tracking",
            "reorder_level",
            "status",  # ← updated to status
            "hsn_code",
            "gst_rate",
            "base_unit",
            "net_weight",
            "purchase_rate",
            "sale_rate",
            "valuation_method",
            "minimum_stock",
            "maximum_stock",
            "reorder_qty",
            "making_time_minutes",
            "lead_time_days",
            "bom_required",
            "material_center",
            "batch_managed",
            "grn_required",
        ]
        for f in compare_fields:
            old = getattr(existing, f, None)
            new = data.get(f)
            if self._normalize_for_compare(f, old) != self._normalize_for_compare(
                f, new
            ):
                return False
        return True

    def create_model_instance(self, validated_data: Dict) -> Item:
        exclude = (
            "_row_number",
            "_original_row_data",
            "updated_at",
            "updated_by",
            "created_at",
        )
        model_data = {k: v for k, v in validated_data.items() if k not in exclude}
        return Item(**model_data)

    def save_data(self) -> Tuple[int, int, int, int]:
        if self.dry_run:
            logger.info(
                "Dry run - skipping save", extra={"module_name": self.MODULE_NAME}
            )
            return len(self.validated_data), 0, 0, 0

        total = len(self.validated_data)
        if total == 0:
            return 0, 0, 0, 0

        inserted = updated = skipped = failed = 0

        for batch_start in range(0, total, self.BATCH_SIZE):
            batch = self.validated_data[batch_start : batch_start + self.BATCH_SIZE]
            for idx, data in enumerate(batch):
                row_num = data.get("_row_number", batch_start + idx + 1)
                code = data.get("item_code", "N/A")
                name = data.get("item_name", "N/A")

                try:
                    existing = Item.objects.filter(
                        item_code__iexact=code, deleted=False
                    ).first()

                    if existing:
                        if self._is_exact_duplicate(existing, data):
                            skipped += 1
                            logger.info(
                                "Skipped exact duplicate item (not an error)",
                                extra={
                                    "row_number": row_num,
                                    "item_code": code,
                                    "item_name": name,
                                    "module": self.MODULE_NAME,
                                },
                            )
                            continue

                        changed = False
                        for k, v in data.items():
                            if k in [
                                "id",
                                "created_at",
                                "created_by",
                                "_row_number",
                                "_original_row_data",
                            ]:
                                continue
                            old = getattr(existing, k, None)
                            if self._normalize_for_compare(
                                k, old
                            ) != self._normalize_for_compare(k, v):
                                setattr(existing, k, v)
                                changed = True

                        if changed:
                            existing.updated_by = self.user
                            existing.updated_at = timezone.now()
                            if (
                                existing.minimum_stock is not None
                                and existing.maximum_stock is not None
                                and existing.minimum_stock > existing.maximum_stock
                            ):
                                raise ValueError(
                                    "Minimum stock cannot exceed maximum stock"
                                )
                            existing.save()
                            updated += 1
                        else:
                            skipped += 1
                    else:
                        instance = self.create_model_instance(data)
                        if (
                            instance.minimum_stock is not None
                            and instance.maximum_stock is not None
                            and instance.minimum_stock > instance.maximum_stock
                        ):
                            raise ValueError(
                                "Minimum stock cannot exceed maximum stock"
                            )
                        instance.save()
                        inserted += 1

                except Exception as e:
                    failed += 1
                    logger.error(
                        f"Save failed row {row_num} - {code}: {str(e)}",
                        extra={"item_name": name},
                        exc_info=True,
                    )
                    # Determine field and value based on error
                    field_name = "unknown"
                    value_str = None
                    if "Minimum stock cannot exceed maximum stock" in str(e):
                        field_name = "minimum_stock"
                        value_str = f"Minimum stock: {data.get('minimum_stock')}, Maximum stock: {data.get('maximum_stock')}"
                    # Add failed record to row_errors
                    self._add_row_error(
                        row_num,
                        [
                            {
                                "field": field_name,
                                "message": f"Error saving record: {str(e)}",
                                "value": value_str,
                            }
                        ],
                        data["_original_row_data"],
                    )

        return inserted, updated, skipped, failed

    def _add_row_error(
        self, row_number: int, errors: List[Dict], row_data: Optional[Dict] = None
    ) -> None:
        if not hasattr(self, "row_errors"):
            self.row_errors = []
        formatted = [
            {
                "field": e.get("field", "unknown"),
                "message": e.get("message", "Validation failed"),
                "value": (
                    str(e.get("value", "")) if e.get("value") is not None else None
                ),
            }
            for e in errors
        ]
        self.row_errors.append(
            {"row_number": row_number, "errors": formatted, "row_data": row_data}
        )

    def _save_errors_to_database(self) -> None:
        if not self.import_log or not getattr(self, "row_errors", None):
            return
        try:
            from imports.models import ImportErrorRow
        except Exception:
            return
        for row in self.row_errors:
            for err in row.get("errors", []):
                try:
                    ImportErrorRow.objects.create(
                        import_log=self.import_log,
                        row_number=row["row_number"],
                        error_type="validation",
                        field_name=err["field"],
                        error_message=err["message"],
                        raw_data=row["row_data"],
                    )
                except Exception as e:
                    logger.error(f"Failed to save ImportErrorRow: {e}")

    def import_data(self) -> Dict[str, Any]:
        logger.info("!!! === THIS IS THE DETAILED ITEM IMPORTER VERSION 2025 === !!!")
        logger.info(
            f"File: {self.file.name if self.file else 'no file'}, User: {self.user}, Dry-run: {self.dry_run}"
        )
        is_valid, error = self.validate_file()
        if not is_valid:
            return {
                "success": False,
                "message": error,
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "import_log_id": "",
                    "row_errors": [],
                },
            }

        try:
            self.create_import_log()
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "import_log_id": "",
                    "row_errors": [],
                },
            }

        success, error = self.parse_file()
        if not success:
            if self.import_log:
                self.import_log.mark_failed(error)
            return {
                "success": False,
                "message": error,
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "import_log_id": str(self.import_log.id) if self.import_log else "",
                    "row_errors": [],
                },
            }

        data_rows = self.parser.get_row_count() if self.parser else 0
        valid_count, error_count = self.validate_all_rows()

        inserted = updated = skipped = failed = 0
        if not self.dry_run and valid_count > 0:
            try:
                inserted, updated, skipped, failed = self.save_data()
            except Exception as e:
                if self.import_log:
                    self.import_log.mark_failed(str(e))
                row_errors_display = [
                    {k: v for k, v in err.items() if k != "row_data"}
                    for err in getattr(self, "row_errors", [])[:10]
                ]
                return {
                    "success": False,
                    "message": f"Error saving data: {str(e)}",
                    "data": {
                        "total_records": data_rows,
                        "inserted": 0,
                        "updated": 0,
                        "skipped": valid_count + error_count,
                        "failed": valid_count + error_count,
                        "success_count": 0,
                        "error_count": valid_count + error_count,
                        "import_log_id": (
                            str(self.import_log.id) if self.import_log else ""
                        ),
                        "row_errors": row_errors_display,
                    },
                }

        if not self.dry_run and getattr(self, "row_errors", None):
            self._save_errors_to_database()

        if self.import_log:
            total_saved = inserted + updated
            total_errors = error_count + failed
            self.import_log.mark_completed(total_saved, total_errors)

        row_errors_all = getattr(self, "row_errors", []) or []
        row_errors_display = [
            {k: v for k, v in err.items() if k != "row_data"}
            for err in row_errors_all[:10]
        ]

        message_parts = []
        if inserted > 0:
            message_parts.append(f"{inserted} records inserted successfully")
        if updated > 0:
            message_parts.append(f"{updated} records updated successfully")
        if skipped > 0:
            message_parts.append(f"{skipped} record skipped successfully")
        if error_count + failed > 0:
            message_parts.append(f"{error_count + failed} records failed")

        return {
            "success": bool(inserted > 0 or updated > 0 or skipped > 0),
            "message": (
                " | ".join(message_parts) if message_parts else "No records processed"
            ),
            "data": {
                "total_records": data_rows,
                "inserted": inserted,
                "updated": updated,
                "skipped": skipped,
                "failed": error_count + failed,
                "success_count": inserted + updated,
                "error_count": error_count + failed,
                "import_log_id": str(self.import_log.id) if self.import_log else "",
                "row_errors": row_errors_display,
            },
        }
