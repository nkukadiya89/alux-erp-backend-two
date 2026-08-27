# UOM Test Data

This directory contains test data files for UOM (Unit of Measurement) bulk import functionality.

## Files

### uom_valid.csv
Sample CSV file with valid UOM data for testing successful imports.

**Columns:**
- `UOM Code` (required): Unique code for the UOM (max 10 characters, will be converted to uppercase)
- `UOM Name` (required): Name of the UOM (max 50 characters)
- `UOM Type` (required): Type of UOM - must be one of: WEIGHT, LENGTH, COUNT
- `Decimal Allowed` (optional): Boolean indicating if decimals are allowed (default: True)
- `Is Active` (optional): Boolean indicating if UOM is active (default: True)

**Example values:**
- UOM Type: WEIGHT (for weight measurements like KG, MT, GM)
- UOM Type: LENGTH (for length measurements like M, CM, FT)
- UOM Type: COUNT (for counting units like PCS, BOX)

### uom_with_errors.csv
Sample CSV file with various validation errors for testing error handling.

**Contains errors:**
- Missing UOM Code
- UOM Code too long (exceeds 10 characters)
- Invalid UOM Type
- Duplicate UOM Codes within the file

## Usage

1. Use `uom_valid.csv` to test successful bulk import
2. Use `uom_with_errors.csv` to test error handling and validation
3. Upload files via the `/api/v1/uom/bulk-import/` endpoint

## Notes

- UOM Code will be automatically converted to uppercase
- UOM Code must be unique across the system
- UOM Type must match one of the predefined choices: WEIGHT, LENGTH, COUNT
- Boolean fields (Decimal Allowed, Is Active) accept: True/False, 1/0, Yes/No (case-insensitive)
- If boolean fields are omitted, they default to True
