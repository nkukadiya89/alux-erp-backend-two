# DiePress Bulk Import Test Data

This directory contains sample CSV files for testing the DiePress bulk import functionality.

## Files

### `die_press_valid.csv`
A valid CSV file with sample DiePress records that should import successfully.

**Columns:**
- `Code` (required, unique, max 50 chars) - Unique code for the die press
- `Name` (required, max 100 chars) - Name of the die press
- `Capacity` (optional, integer) - Capacity of the press
- `Billet Diameter` (optional, integer) - Billet diameter
- `Billet Length Min` (optional, integer) - Minimum billet length
- `Billet Length Max` (optional, integer) - Maximum billet length
- `Billet Weight` (optional, float) - Billet weight
- `Extrusion Length Min` (optional, integer) - Minimum extrusion length
- `Extrusion Length Max` (optional, integer) - Maximum extrusion length

### `die_press_with_errors.csv`
A CSV file with intentional errors for testing validation:

1. **Row 3**: Duplicate code (PRESS001) - should fail uniqueness validation
2. **Row 4**: Invalid integer value for Capacity (Invalid) - should fail validation
3. **Row 5**: Invalid integer value for Billet Diameter (Invalid) - should fail validation
4. **Row 6**: Invalid integer value for Billet Length Min (Invalid) - should fail validation

## Expected Outcomes

### For `die_press_valid.csv`:
- All 5 records should import successfully
- All fields should be populated correctly
- No errors should be reported

### For `die_press_with_errors.csv`:
- Row 2 should import successfully (PRESS001, Press Machine 1)
- Row 3 should fail due to duplicate code (PRESS001)
- Row 4 should fail due to invalid Capacity value
- Row 5 should fail due to invalid Billet Diameter value
- Row 6 should fail due to invalid Billet Length Min value

## Usage

Use these files to test the bulk import API endpoint:
- **Endpoint**: `POST /api/v1/die-press/bulk-import/`
- **File Upload**: Upload the CSV file using the `file` field
- **Dry Run**: Use `dry_run=true` to validate without saving
