# Alloy Bulk Import - Test Data

This directory contains test files for testing the Alloy Master bulk import functionality.

## Files

1. **alloy_valid.csv** - Sample CSV file with valid alloy records
2. **alloy_with_errors.csv** - Sample CSV file with intentional errors for testing error handling
3. **README.md** - This documentation file

## CSV File Format

### Required Columns
- **Alloy Code** - Alloy code (max 25 characters)
- **Standard Name** - Standard name for the alloy (max 50 characters)

### Optional Columns
- **Color Code** - Color code (max 50 characters)
- **SI Min** - Silicon minimum (decimal, max 10 digits, 3 decimal places)
- **SI Max** - Silicon maximum (decimal, max 10 digits, 3 decimal places)
- **MG Min** - Magnesium minimum (decimal, max 10 digits, 3 decimal places)
- **MG Max** - Magnesium maximum (decimal, max 10 digits, 3 decimal places)
- **FE Min** - Iron minimum (decimal, max 10 digits, 3 decimal places)
- **FE Max** - Iron maximum (decimal, max 10 digits, 3 decimal places)
- **MN Min** - Manganese minimum (decimal, max 10 digits, 3 decimal places)
- **MN Max** - Manganese maximum (decimal, max 10 digits, 3 decimal places)
- **CU Min** - Copper minimum (decimal, max 10 digits, 3 decimal places)
- **CU Max** - Copper maximum (decimal, max 10 digits, 3 decimal places)
- **ZN Min** - Zinc minimum (decimal, max 10 digits, 3 decimal places)
- **ZN Max** - Zinc maximum (decimal, max 10 digits, 3 decimal places)
- **CR Min** - Chromium minimum (decimal, max 10 digits, 3 decimal places)
- **CR Max** - Chromium maximum (decimal, max 10 digits, 3 decimal places)
- **TI Min** - Titanium minimum (decimal, max 10 digits, 3 decimal places)
- **TI Max** - Titanium maximum (decimal, max 10 digits, 3 decimal places)
- **BI Min** - Bismuth minimum (decimal, max 10 digits, 3 decimal places)
- **BI Max** - Bismuth maximum (decimal, max 10 digits, 3 decimal places)
- **PB Min** - Lead minimum (decimal, max 10 digits, 3 decimal places)
- **PB Max** - Lead maximum (decimal, max 10 digits, 3 decimal places)
- **SN Min** - Tin minimum (decimal, max 10 digits, 3 decimal places)
- **SN Max** - Tin maximum (decimal, max 10 digits, 3 decimal places)
- **Others Each Min** - Others each minimum (decimal, max 10 digits, 3 decimal places)
- **Others Each Max** - Others each maximum (decimal, max 10 digits, 3 decimal places)
- **Others Total Min** - Others total minimum (decimal, max 10 digits, 3 decimal places)
- **Others Total Max** - Others total maximum (decimal, max 10 digits, 3 decimal places)
- **AL Min** - Aluminum minimum (decimal, max 10 digits, 3 decimal places)
- **AL Max** - Aluminum maximum (decimal, max 10 digits, 3 decimal places)
- **Remark** - Remarks (max 250 characters)

## Data Format

### Alloy Code
- Required field
- Maximum 25 characters
- Must be unique in combination with Standard Name and Color Code
- Examples: `6061`, `6063`, `6082`, `7075`

### Standard Name
- Required field
- Maximum 50 characters
- Must be unique in combination with Alloy Code and Color Code
- Examples: `EN AW-6061`, `EN AW-6063`, `EN AW-6082`

### Color Code
- Optional field
- Maximum 50 characters
- Part of the unique combination (Alloy Code + Standard Name + Color Code)
- Examples: `Natural`, `Black`, `Silver`

### Decimal Fields
- All decimal fields accept numeric values with up to 3 decimal places
- Invalid decimal values will be set to None
- Min values should not exceed corresponding Max values (validation in serializer)
- Examples: `0.400`, `0.800`, `95.800`

### String Fields
- All string fields accept text values
- Maximum lengths are enforced
- Examples: `Standard aluminum alloy`, `Extruded profiles`

## Expected Results

### alloy_valid.csv
- **Total Rows**: 10
- **Success Count**: 10 (assuming no duplicates exist in database)
- **Error Count**: 0
- **Status**: Completed

### alloy_with_errors.csv
- **Total Rows**: 7
- **Success Count**: 2 (assuming "6061" and "3003" combinations are already in DB from valid import)
- **Error Count**: 5
- **Status**: Partial Success

### Errors in alloy_with_errors.csv:

1. **Row 3**: Duplicate combination (Alloy Code: 6061, Standard Name: EN AW-6061, Color Code: Natural) - duplicate within file
2. **Row 4**: Empty Alloy Code - required field is empty
3. **Row 5**: Empty Standard Name - required field is empty
4. **Row 6**: Invalid Decimal Value ("INVALID_DECIMAL" for SI Min) - cannot be converted to decimal
5. **Row 7**: Color Code Too Long - exceeds maximum length of 50 characters
6. **Row 8**: Min Greater Than Max - SI Min (0.000) should be less than or equal to SI Max (0.250), but this is actually valid. The error might be for a different field pair.

## Testing Workflow

### Step 1: Prepare Test Data
1. Ensure your database is clean or you understand potential duplicate errors.
2. Note: Alloy uniqueness is based on the combination of (alloy_code, standard_name, color_code)

### Step 2: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/alloy/bulk-import/`
3. Upload `alloy_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 3: Import Valid Data
1. POST to `/api/v1/alloy/bulk-import/`
2. Upload `alloy_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

### Step 4: Test Error Handling
1. POST to `/api/v1/alloy/bulk-import/`
2. Upload `alloy_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

### Step 5: View Import Logs
1. GET `/api/v1/alloy/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 6: View Errors
1. GET `/api/v1/alloy/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 7: Download Error Report
1. GET `/api/v1/alloy/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 8: Verify Imported Data
1. GET `/api/v1/alloy/` to see imported alloys
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/alloy/dropdown/`

## Notes

- Uniqueness is based on the combination of (alloy_code, standard_name, color_code)
- Decimal fields are validated for proper format
- String fields are trimmed and normalized
- Min/Max fields are validated to ensure Min <= Max (in serializer)
- All fields except Alloy Code and Standard Name are optional
- Invalid decimal values are set to None (not rejected)
