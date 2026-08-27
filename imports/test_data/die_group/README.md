# DieGroup Bulk Import Test Data

This directory contains sample CSV files for testing the DieGroup bulk import functionality.

## Files

1. **die_group_valid.csv**: Contains valid data for successful imports
   - All required fields are present
   - All names are unique
   - All names are within the 50 character limit
   - Expected outcome: All rows should be imported successfully

2. **die_group_with_errors.csv**: Contains data with intentional errors to test error handling
   - Row 3: Duplicate name "Group B" (should fail uniqueness validation)
   - Row 4: Name exceeds 50 character limit (should fail length validation)
   - Expected outcome: Import should fail with validation errors

## Column Specifications

### Required Columns
- **Name** (string, max 50 characters, unique, required)
  - The name of the die group
  - Must be unique across all die groups
  - Maximum length: 50 characters
  - Cannot be empty or null

## Usage

1. **Valid Import Test**:
   - Use `die_group_valid.csv` for testing successful bulk imports
   - Expected: All rows imported successfully

2. **Error Handling Test**:
   - Use `die_group_with_errors.csv` for testing error handling
   - Expected: Import fails with specific validation errors for problematic rows

## Notes

- All CSV files use UTF-8 encoding
- Headers are case-sensitive and must match exactly: `Name`
- Empty rows are ignored
- Whitespace in names is automatically trimmed
