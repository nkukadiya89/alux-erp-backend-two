# PackingMode Bulk Import Test Data

This directory contains sample CSV files for testing the PackingMode bulk import functionality.

## Files

1. **packing_mode_valid.csv**: Contains valid data for successful imports
   - All required fields are present
   - All names are unique
   - All fields are within their respective limits and types
   - Expected outcome: All rows should be imported successfully

2. **packing_mode_with_errors.csv**: Contains data with intentional errors to test error handling
   - Row 3: Duplicate name "Loose Packing" (should fail uniqueness validation)
   - Row 4: Empty name (should fail required field validation)
   - Expected outcome: Import fails with specific validation errors for problematic rows

## Column Specifications

### Required Columns
- **Name** (string, max 100 characters, unique, required)
  - The name of the packing mode.
  - Must be unique across all packing modes.
  - Maximum length: 100 characters.
  - Cannot be empty or null.

### Optional Columns
- **Description** (text, optional)
  - Description of the packing mode.
  - Can be empty or null.

## Usage

1. **Valid Import Test**:
   - Use `packing_mode_valid.csv` for testing successful bulk imports.
   - Expected: All rows imported successfully.

2. **Error Handling Test**:
   - Use `packing_mode_with_errors.csv` for testing error handling.
   - Expected: Import fails with specific validation errors for problematic rows.

## Notes

- All CSV files use UTF-8 encoding.
- Headers are case-insensitive and must match exactly (e.g., `Name` or `name`).
- Empty rows are ignored.
- Whitespace in string fields is automatically trimmed.
