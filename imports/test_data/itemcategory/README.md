# Item Category Bulk Import - Test Data

This directory contains test files for testing the Item Category Master bulk import functionality.

## Files

1. **item_category_valid.csv** - Sample CSV file with 25 valid item category records
2. **item_categories_with_errors.csv** - Sample CSV file with intentional errors for testing error handling

## CSV File Format

### Required Columns
- **Category Code** - Unique category code (alphanumeric with hyphens/underscores, will be converted to uppercase)
- **Category Name** - Category name (max 255 characters)
- **Allowed Item Type** - One of: RAW, CONSUMABLE, SEMI, FG, SPARE, SCRAP, TOOLING

### Optional Columns
- **Description** - Category description (text field, optional)
- **Is Active** - TRUE or FALSE (defaults to TRUE if not provided)

## Data Format

### Category Code
- Alphanumeric with hyphens/underscores
- Unique (case-insensitive)
- Will be automatically converted to uppercase
- Examples: `AL-INGOT`, `CAT-001`, `MRO_MECH`
- Maximum 50 characters

### Category Name
- Free text field
- Required field
- Maximum 255 characters
- Examples: "Aluminum Ingots", "Flux & Refining Chemicals"

### Allowed Item Type
Valid values (case-insensitive):
- `RAW` - Raw Material
- `CONSUMABLE` - Consumable
- `SEMI` - Semi-Finished
- `FG` - Finished Goods
- `SPARE` - Spare Parts
- `SCRAP` - Scrap
- `TOOLING` - Tooling

### Description
- Optional field
- Free text description
- Can be empty/null
- No maximum length restriction (stored as TextField)

### Is Active
- Boolean field
- Valid values: `TRUE`, `FALSE` (case-insensitive)
- Defaults to `TRUE` if not provided
- Determines if category appears in dropdown APIs

## Expected Results

### item_category_valid.csv
- **Total Rows**: 25
- **Success Count**: 25
- **Error Count**: 0
- **Status**: Completed

**Categories Included:**
- **RAW (8 categories)**: Aluminum Ingots, Scrap, Alloying Elements, Wire Rod, Sheets, Powder
- **CONSUMABLE (6 categories)**: Flux, Refractory Materials, Gases, Lubricants, Packing, Utility Materials
- **SEMI (3 categories)**: Billets, WIP Materials, Semi-Finished Castings
- **FG (3 categories)**: Extruded Profiles, Fabricated Parts, Assembled Products
- **TOOLING (2 categories)**: Extrusion Dies, Die Accessories
- **SPARE (3 categories)**: Mechanical, Electrical, Hydraulic Spares
- **SCRAP (2 categories)**: Process Scrap, Dross & Skimmings

### item_categories_with_errors.csv
- **Total Rows**: 15
- **Success Count**: 6 (rows 1, 4, 6, 8, 10, 12, 14)
- **Error Count**: 9
- **Status**: Partial Success

### Errors in item_categories_with_errors.csv:

1. **Row 2**: Duplicate Category Code (CAT-101) - duplicate within file
2. **Row 3**: Invalid Allowed Item Type - "INVALID_TYPE" is not a valid choice
3. **Row 4**: Missing Category Name - required field is empty
4. **Row 6**: Invalid Is Active Value - "INVALID" is not a valid boolean (must be TRUE/FALSE)
5. **Row 8**: Empty Category Code - required field is empty
6. **Row 10**: Invalid Allowed Item Type - "SSCRAP" is not a valid choice (typo)
7. **Row 12**: Duplicate Category Code (CAT-111) - another duplicate within file
8. **Row 14**: Invalid Allowed Item Type - "SEMIFINISHED" is not valid (should be SEMI)
9. **Row 16**: Special Characters in Code - may fail pattern validation

## Testing Workflow

### Step 1: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/item-categories/bulk-import/`
3. Upload `item_category_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 2: Import Valid Data
1. POST to `/api/v1/item-categories/bulk-import/`
2. Upload `item_category_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

**Expected Response:**
```json
{
    "success": true,
    "message": "Import completed: 25 successful, 0 errors",
    "data": {
        "import_log_id": "...",
        "total_rows": 25,
        "total_records": 25,
        "inserted": 25,
        "updated": 0,
        "skipped": 0,
        "success_count": 25,
        "error_count": 0,
        "dry_run": false
    }
}
```

### Step 3: Test Error Handling
1. POST to `/api/v1/item-categories/bulk-import/`
2. Upload `item_categories_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

**Expected Response:**
```json
{
    "success": true,
    "message": "Import completed: 6 successful, 9 errors",
    "data": {
        "import_log_id": "...",
        "total_rows": 15,
        "total_records": 15,
        "inserted": 6,
        "updated": 0,
        "skipped": 9,
        "success_count": 6,
        "error_count": 9,
        "dry_run": false,
        "row_errors": [
            {
                "row_number": 2,
                "error_type": "validation",
                "field_name": "category_code",
                "error_message": "Category code already exists in this file",
                "raw_data": {...}
            },
            ...
        ]
    }
}
```

### Step 4: View Import Logs
1. GET `/api/v1/item-categories/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 5: View Errors
1. GET `/api/v1/item-categories/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 6: Download Error Report
1. GET `/api/v1/item-categories/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 7: Verify Imported Data
1. GET `/api/v1/item-categories/` to see imported categories
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/item-categories/dropdown/`
4. Test filtered dropdown: GET `/api/v1/item-categories/dropdown/?item_type=RAW`

## Sample Data Description

### item_category_valid.csv Contains:

**Raw Material Categories (8):**
- AL-INGOT: Aluminum Ingots
- AL-SCRAP: Aluminum Scrap
- AL-ALLOY: Alloying Elements
- WIRE-RAW: Aluminum Wire Rod
- SHEET-RAW: Aluminum Sheets
- POWDER: Aluminum Powder

**Consumable Categories (6):**
- FLUX: Flux & Refining Chemicals
- REFRACT: Refractory Materials
- GAS: Industrial Gases
- LUBE: Lubricants & Oils
- PACK: Packing Materials
- UTILITY: Utility Materials

**Semi-Finished Categories (3):**
- BILLET: Aluminum Billets
- WIP-MAT: WIP Materials
- CASTING: Semi-Finished Castings

**Finished Goods Categories (3):**
- PROFILE: Extruded Profiles
- FAB-PART: Fabricated Parts
- ASSEMBLY: Assembled Products

**Tooling Categories (2):**
- DIE: Extrusion Dies
- DIE-ACC: Die Accessories

**Spare Parts Categories (3):**
- MRO-MECH: Mechanical Spares
- MRO-ELEC: Electrical Spares
- MRO-HYD: Hydraulic Spares

**Scrap Categories (2):**
- SCRAP-PROC: Process Scrap
- SCRAP-DROSS: Dross & Skimmings

## Validation Rules

### Category Code Validation
- Required field
- Must be unique (case-insensitive)
- Pattern: `^[A-Z0-9_-]+$` (alphanumeric, hyphens, underscores)
- Maximum 50 characters
- Automatically converted to uppercase

### Category Name Validation
- Required field
- Maximum 255 characters
- Cannot be empty or whitespace only

### Allowed Item Type Validation
- Required field
- Must be one of the predefined choices:
  - RAW, CONSUMABLE, SEMI, FG, SPARE, SCRAP, TOOLING
- Case-insensitive matching

### Description Validation
- Optional field
- No length restriction
- Can be empty/null

### Is Active Validation
- Optional field (defaults to TRUE)
- Must be TRUE or FALSE (case-insensitive)
- Accepts: "TRUE", "True", "true", "1", "YES", "Yes", "yes"
- Accepts: "FALSE", "False", "false", "0", "NO", "No", "no"

## Important Notes

1. **Case Sensitivity**: Category codes are case-insensitive (AL-INGOT = al-ingot)
2. **Code Normalization**: Category codes are automatically converted to uppercase
3. **Duplicate Handling**: Duplicates within file are rejected during validation
4. **Database Uniqueness**: Existing category codes in database are rejected (unless archived)
5. **Active Status**: Inactive categories don't appear in dropdown APIs
6. **Item Type Filtering**: Dropdown API can filter by `item_type` parameter
7. **Batch Processing**: Large imports (>1000 rows) are processed asynchronously

## Troubleshooting

### Category Code Already Exists Error
- Category code must be unique (case-insensitive)
- Check if category already exists in database
- Archived categories can be restored instead of recreated
- Use different codes for new categories

### Invalid Allowed Item Type Error
- Must be exactly one of: RAW, CONSUMABLE, SEMI, FG, SPARE, SCRAP, TOOLING
- Check for typos (e.g., "CONSUMABLES" instead of "CONSUMABLE")
- Case-insensitive but must match exactly

### Validation Errors
- Check error report for detailed messages
- Verify all required fields are present
- Ensure data types match expected format
- Check field length restrictions

### Duplicate Within File Error
- Category codes must be unique within the same import file
- Remove duplicate rows or use different codes

### Pattern Validation Error
- Category code must match pattern: `^[A-Z0-9_-]+$`
- Only alphanumeric characters, hyphens, and underscores allowed
- Special characters like @, #, $, %, etc. are not allowed

### Missing Required Field Error
- Category Code and Category Name are required
- Cannot be empty or whitespace only
- Allowed Item Type is also required

## API Endpoints Reference

- **Bulk Import**: `POST /api/v1/item-categories/bulk-import/`
- **Import Logs**: `GET /api/v1/item-categories/import-logs/`
- **Import Errors**: `GET /api/v1/item-categories/{import_log_id}/import-errors/`
- **Download Error Report**: `GET /api/v1/item-categories/{import_log_id}/error-report/download/`
- **List Categories**: `GET /api/v1/item-categories/`
- **Dropdown**: `GET /api/v1/item-categories/dropdown/`
- **Filtered Dropdown**: `GET /api/v1/item-categories/dropdown/?item_type=RAW`

