# Temper Bulk Import - Test Data

This directory contains test files for testing the Temper Master bulk import functionality.

## Files

1. **temper_valid.csv** - Sample CSV file with valid temper records
2. **temper_with_errors.csv** - Sample CSV file with intentional errors for testing error handling
3. **README.md** - This documentation file

## CSV File Format

### Required Columns
- **Name** - Unique name for the temper (max 25 characters)

### Optional Columns
- **Code** - Temper code (max 50 characters)
- **Section Type** - Name of SectionType (must exist in database, case-insensitive lookup)
- **Area** - Decimal field (max 10 digits, 3 decimal places)
- **Dimension Unit** - Unit of measurement (max 10 characters)
- **Elongation 50mm Min** - Decimal field (max 10 digits, 2 decimal places)
- **Elongation Min** - Decimal field (max 10 digits, 2 decimal places)
- **Hardness** - Decimal field (max 5 digits, 2 decimal places)
- **Section Thickness Over** - String field (max 50 characters)
- **Section Thickness Upto** - String field (max 50 characters)
- **Tensile Min** - Decimal field (max 6 digits, 2 decimal places)
- **Tensile Max** - Decimal field (max 6 digits, 2 decimal places)
- **Yield Min** - Decimal field (max 6 digits, 2 decimal places)
- **Yield Max** - Decimal field (max 6 digits, 2 decimal places)
- **Yield Unit** - Unit of measurement (max 10 characters)
- **Electrical Conductivity Min** - Decimal field (max 5 digits, 2 decimal places)
- **Electrical Conductivity Max** - Decimal field (max 5 digits, 2 decimal places)
- **Temper Code Old** - Old temper code (max 20 characters)
- **Temper Code New** - New temper code (max 20 characters)

## Data Format

### Name
- Must be unique (case-insensitive)
- Maximum 25 characters
- Required field
- Examples: `T4`, `T5`, `T6`, `O`, `H112`

### Code
- Optional field
- Maximum 50 characters
- Examples: `AL-T4`, `AL-T5`, `AL-T6`

### Section Type
- Optional foreign key field
- Must match an existing SectionType name in the database (case-insensitive)
- Examples: `Solid`, `Hollow`

### Decimal Fields
- All decimal fields accept numeric values
- Invalid decimal values will be set to None
- Examples: `125.500`, `8.50`, `75.00`

### String Fields
- All string fields accept text values
- Maximum lengths are enforced
- Examples: `mm`, `MPa`, `T4`

## Expected Results

### temper_valid.csv
- **Total Rows**: 10
- **Success Count**: 10
- **Error Count**: 0
- **Status**: Completed

### temper_with_errors.csv
- **Total Rows**: 7
- **Success Count**: 2 (assuming "T4" and "T5" are already in DB from valid import)
- **Error Count**: 5
- **Status**: Partial Success

### Errors in temper_with_errors.csv:

1. **Row 3**: Duplicate Name ("T4") - duplicate within file
2. **Row 4**: Empty Name - required field is empty
3. **Row 5**: Invalid Section Type ("InvalidSectionType") - SectionType not found in database
4. **Row 6**: Invalid Decimal Value ("INVALID_DECIMAL" for Area) - cannot be converted to decimal
5. **Row 7**: Code Too Long - exceeds maximum length of 50 characters

## Testing Workflow

### Step 1: Prepare Test Data
1. Ensure your database has SectionType records (e.g., "Solid", "Hollow")
2. Ensure your database is clean or you understand potential duplicate errors.

### Step 2: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/temper/bulk-import/`
3. Upload `temper_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 3: Import Valid Data
1. POST to `/api/v1/temper/bulk-import/`
2. Upload `temper_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

### Step 4: Test Error Handling
1. POST to `/api/v1/temper/bulk-import/`
2. Upload `temper_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

### Step 5: View Import Logs
1. GET `/api/v1/temper/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 6: View Errors
1. GET `/api/v1/temper/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 7: Download Error Report
1. GET `/api/v1/temper/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 8: Verify Imported Data
1. GET `/api/v1/temper/` to see imported tempers
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/temper/dropdown/`

## Notes

- Section Type lookup is case-insensitive
- Decimal fields are validated for proper format
- String fields are trimmed and normalized
- All fields except Name are optional
- Name must be unique across the entire database (case-insensitive)
