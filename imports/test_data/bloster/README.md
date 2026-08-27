# BlosterMaster Bulk Import - Test Data

This directory contains test files for testing the BlosterMaster bulk import functionality.

## Files

1. **bloster_valid.csv** - Sample CSV file with 10 valid bloster records
2. **bloster_with_errors.csv** - Sample CSV file with intentional errors for testing error handling

## CSV File Format

### Required Columns
- **Bloster No** - Bloster number (max 100 characters, unique)
- **Press Name** - DiePress name (must exist in DiePress master, case-insensitive lookup)

### Optional Columns
- **Bloster Image** - Bloster image file path (max 250 characters)
- **Autocard** - Autocard file path (max 250 characters)
- **PDF** - PDF file path (max 250 characters)

## Data Format

### Bloster No
- Bloster number identifier
- Maximum 100 characters
- Must be unique (case-insensitive)
- Required field (cannot be empty/null)
- Examples: "BL001", "BL-001-2024"

### Press Name
- DiePress name reference (must exist in DiePress master)
- Case-insensitive lookup
- DiePress must be active (deleted=False)
- Required field (cannot be empty/null)
- Examples: "Press 1000T", "Press 2000T"

### Bloster Image
- Bloster image file path
- Maximum 250 characters
- Optional field (can be empty/null)
- Examples: "path/to/image.jpg", "path/to/image.png"

### Autocard
- Autocard file path
- Maximum 250 characters
- Optional field (can be empty/null)
- Examples: "path/to/autocard.dwg"

### PDF
- PDF file path
- Maximum 250 characters
- Optional field (can be empty/null)
- Examples: "path/to/document.pdf"

## Expected Results

### bloster_valid.csv
- **Total Rows**: 10
- **Success Count**: 10 (assuming no duplicates exist in database and Press names exist)
- **Error Count**: 0
- **Status**: Completed

**Note**: If some bloster numbers already exist in your database, those rows will fail with "duplicate bloster number" error. The import will skip duplicates and create new ones.

### bloster_with_errors.csv
- **Total Rows**: 6
- **Success Count**: 2 (rows 1, 4)
- **Error Count**: 4
- **Status**: Partial Success

### Errors in bloster_with_errors.csv:

1. **Row 2**: Duplicate Bloster No - "BL001" is duplicated within the file (row 1 and row 2)
2. **Row 3**: Invalid Press Name - "Invalid Press" does not exist in DiePress master
3. **Row 5**: Missing Press Name - Press Name is empty (required field)

## Testing Workflow

### Step 1: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/bloster/bulk-import/`
3. Upload `bloster_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 2: Import Valid Data
1. POST to `/api/v1/bloster/bulk-import/`
2. Upload `bloster_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

### Step 3: Test Error Handling
1. POST to `/api/v1/bloster/bulk-import/`
2. Upload `bloster_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

### Step 4: View Import Logs
1. GET `/api/v1/bloster/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 5: View Errors
1. GET `/api/v1/bloster/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 6: Download Error Report
1. GET `/api/v1/bloster/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 7: Verify Imported Data
1. GET `/api/v1/bloster/` to see imported blosters
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/bloster/dropdown/`

## Sample Data Description

### bloster_valid.csv Contains:

**10 Blosters:**
- BL001: Press 1000T
- BL002: Press 2000T
- BL003: Press 1500T
- BL004: Press 2500T
- BL005: Press 1000T
- BL006: Press 2000T
- BL007: Press 1500T
- BL008: Press 2500T
- BL009: Press 1000T
- BL010: Press 2000T

## Important Notes

1. **Bloster No Uniqueness**: Bloster numbers must be unique (case-insensitive)
2. **Bloster No Length**: Maximum 100 characters
3. **Required Fields**: Bloster No and Press Name are required
4. **Press Reference**: Press name must exist in DiePress master and be active (not deleted)
5. **Case Sensitivity**: Bloster numbers are case-insensitive for uniqueness check (e.g., "BL001" = "bl001")
6. **Duplicate Handling**: If a bloster with the same number already exists in the database, the import will fail for that row

## Troubleshooting

### Duplicate Bloster No Errors
- Bloster numbers must be unique (case-insensitive)
- Check if bloster already exists in database
- Use different numbers for new blosters
- The import will fail for duplicate numbers within the file and against existing database records

### Invalid Press Name Errors
- Press name must exist in DiePress master
- Press must be active (not deleted)
- Check if press name exists in database
- Verify press name spelling and case (case-insensitive lookup)

### Validation Errors
- Check error report for detailed messages
- Verify all required fields are present
- Ensure data types match expected format
- Bloster No and Press Name fields cannot be empty or null
