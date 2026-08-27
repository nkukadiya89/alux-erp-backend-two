# Item Master Test Data

This directory contains test data files for Item Master bulk import functionality.

## Files

- `item_valid.csv` - Sample valid data for testing successful imports
- `item_with_errors.csv` - Sample data with various errors for testing validation

## File Format

### Required Columns

- **Item Code** (required, unique, max 100 chars) - Unique item code (case-insensitive, will be converted to uppercase)
- **Item Name** (required, max 255 chars) - Item name
- **Item Type** (required) - Must be one of: RAW, CONSUMABLE, SEMI, FG
- **Category Code** (required) - ItemCategory code (must exist, must be active and not archived)
- **Default UOM Code** (required) - UOM code for default unit of measurement (must exist, must be active and not deleted)

### Optional Columns

- **Secondary UOM Code** - UOM code for secondary unit of measurement (must exist, must be active and not deleted)
- **Conversion Factor** (required if Secondary UOM is provided) - Decimal value for conversion between UOMs (max 10 digits, 4 decimal places)
- **Alloy Code** (max 50 chars) - Alloy code reference
- **Heat Tracking** (boolean) - TRUE/FALSE, YES/NO, 1/0 (default: FALSE)
  - **Note**: Must be TRUE for RAW item type
- **Reorder Level** (decimal) - Reorder level value (max 10 digits, 2 decimal places)
- **Is Active** (boolean) - TRUE/FALSE, YES/NO, 1/0 (default: TRUE)

## Validation Rules

1. **Item Code**: Must be unique (case-insensitive), will be converted to uppercase
2. **Item Type**: Must be one of: RAW, CONSUMABLE, SEMI, FG
3. **Category**: Must exist in ItemCategory table, must be active (is_active=True) and not archived (is_archived=False)
4. **Default UOM**: Must exist in UOM table, must be active (is_active=True) and not deleted (deleted=False)
5. **Secondary UOM**: If provided, must exist in UOM table, must be active and not deleted
6. **Conversion Factor**: Required when Secondary UOM is provided
7. **Heat Tracking**: Must be TRUE for RAW item type
8. **Uniqueness**: Item codes must be unique across all non-deleted items

## Sample Data Notes

### Valid Data (item_valid.csv)

- Contains 8 sample items with various item types
- Includes examples with and without secondary UOM
- Shows RAW items with heat tracking enabled
- Demonstrates different category and UOM combinations

### Error Data (item_with_errors.csv)

Contains examples of various validation errors:

1. Missing Item Code
2. Missing Item Name
3. Invalid Item Type (INVALID_TYPE)
4. Invalid Category Code (doesn't exist)
5. Invalid Default UOM Code (doesn't exist)
6. Missing Conversion Factor (when Secondary UOM is provided)
7. RAW item without Heat Tracking (must be TRUE)
8. Duplicate Item Codes (within file)

## Usage

1. Use `item_valid.csv` to test successful bulk imports
2. Use `item_with_errors.csv` to test error handling and validation
3. Ensure required ItemCategory and UOM records exist in the database before importing
4. Check import logs and error reports after import

## Notes

- All Item Codes will be converted to uppercase
- Category Code lookups are case-insensitive
- UOM Code lookups are case-insensitive
- Boolean fields accept: TRUE/FALSE, YES/NO, 1/0
- Decimal fields support various formats (will be normalized)
