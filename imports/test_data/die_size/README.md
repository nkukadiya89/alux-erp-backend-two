# DieSize Bulk Import Test Data

This directory contains sample CSV files for testing the DieSize bulk import functionality.

## Files

1. **die_size_valid.csv**: Contains valid data for successful imports
   - All required fields are present (die_height, die_width)
   - All combinations are unique
   - All values are valid decimals
   - Expected outcome: All rows should be imported successfully

2. **die_size_with_errors.csv**: Contains data with intentional errors to test error handling
   - Row 3: Duplicate combination (die_height=15.25, die_width=25.50) - should be allowed but logged as duplicate in file
   - Row 5: Values exceed max_digits (10 digits) - should fail validation
   - Expected outcome: Import should fail with validation errors

## Column Specifications

### Required Columns
- **Die Height** (decimal, max_digits=10, decimal_places=2, required)
  - The height of the die
  - Must be a valid decimal number
  - Maximum 10 digits total, 2 decimal places
  
- **Die Width** (decimal, max_digits=10, decimal_places=2, required)
  - The width of the die
  - Must be a valid decimal number
  - Maximum 10 digits total, 2 decimal places

### Important Notes
- DieSize has no unique field constraint on individual fields
- Combination of die_height + die_width should be unique (but no database constraint)
- Duplicate combinations in the import file will be tracked and logged
- The importer validates combination uniqueness within the file

## Usage

1. Use `die_size_valid.csv` to test successful imports
2. Use `die_size_with_errors.csv` to test error handling and validation
3. Both files use column headers matching the field mapping ("Die Height", "Die Width")
