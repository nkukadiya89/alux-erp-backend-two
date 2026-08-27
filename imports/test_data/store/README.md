# Store Bulk Import - Test Data

This directory contains test files for testing the Store Master bulk import functionality.

## Files

1. **store_valid.csv** - Sample CSV file with 10 valid store records
2. **store_with_errors.csv** - Sample CSV file with intentional errors for testing error handling

## CSV File Format

### Required Columns
- **Store Code** - Store code (max 30 characters, unique)
- **Store Name** - Store name (max 100 characters)
- **Store Type** - Store type (RAW, SCRAP, BILLET, FG, WIP)
- **Plant Code** - Plant code (must exist in Plant master, case-insensitive lookup)

### Optional Columns
- **Allows Negative Stock** - Boolean (True/False, defaults to False if not provided)

## Data Format

### Store Code
- Store code identifier
- Maximum 30 characters
- Must be unique (case-insensitive)
- Required field (cannot be empty/null)
- Examples: "ST001", "MAIN-RAW-001"

### Store Name
- Store name/description
- Maximum 100 characters
- Required field (cannot be empty/null)
- Examples: "Main Raw Material Store", "Finished Goods Warehouse"

### Store Type
- Store type (must be one of: RAW, SCRAP, BILLET, FG, WIP)
- Case-insensitive
- Required field (cannot be empty/null)
- Valid values:
  - RAW - Raw material store
  - SCRAP - Scrap storage
  - BILLET - Billet warehouse
  - FG - Finished Goods
  - WIP - Work In Progress

### Plant Code
- Plant code reference (must exist in Plant master)
- Case-insensitive lookup
- Plant must be active (deleted=False)
- Required field (cannot be empty/null)
- Examples: "PLT001", "PLT002"

### Allows Negative Stock
- Boolean field indicating if store allows negative stock
- Optional field (defaults to False if not provided)
- Valid values: True, False, true, false, 1, 0, Yes, No, Y, N
- Case-insensitive

## Expected Results

### store_valid.csv
- **Total Rows**: 10
- **Success Count**: 10 (assuming no duplicates exist in database and Plant codes exist)
- **Error Count**: 0
- **Status**: Completed

**Note**: If some store codes already exist in your database, those rows will fail with "duplicate store code" error. The import will skip duplicates and create new ones.

### store_with_errors.csv
- **Total Rows**: 7
- **Success Count**: 4 (rows 1, 3, 5, 7)
- **Error Count**: 3
- **Status**: Partial Success

### Errors in store_with_errors.csv:

1. **Row 2**: Duplicate Store Code - "ST001" is duplicated within the file (row 1 and row 2)
2. **Row 4**: Invalid Store Type - "INVALID" is not a valid StoreType choice
3. **Row 6**: Invalid Plant Code - "INVALID_PLANT" does not exist in Plant master

## Testing Workflow

### Step 1: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/stores/bulk-import/`
3. Upload `store_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 2: Import Valid Data
1. POST to `/api/v1/stores/bulk-import/`
2. Upload `store_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

### Step 3: Test Error Handling
1. POST to `/api/v1/stores/bulk-import/`
2. Upload `store_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

### Step 4: View Import Logs
1. GET `/api/v1/stores/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 5: View Errors
1. GET `/api/v1/stores/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 6: Download Error Report
1. GET `/api/v1/stores/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 7: Verify Imported Data
1. GET `/api/v1/stores/` to see imported stores
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/stores/dropdown/`

## Sample Data Description

### store_valid.csv Contains:

**10 Stores:**
- ST001: Main Raw Material Store (RAW, PLT001)
- ST002: Scrap Storage (SCRAP, PLT001)
- ST003: Billet Warehouse (BILLET, PLT001)
- ST004: Finished Goods Warehouse (FG, PLT001, allows negative stock)
- ST005: Work In Progress Store (WIP, PLT001)
- ST006: Secondary Raw Store (RAW, PLT002)
- ST007: Scrap Collection Point (SCRAP, PLT002)
- ST008: Production Store (WIP, PLT002)
- ST009: Main Finished Goods (FG, PLT002, allows negative stock)
- ST010: Billet Storage Area (BILLET, PLT002)

## Important Notes

1. **Store Code Uniqueness**: Store codes must be unique (case-insensitive)
2. **Store Code Length**: Maximum 30 characters
3. **Store Name Length**: Maximum 100 characters
4. **Required Fields**: Store Code, Store Name, Store Type, and Plant Code are required
5. **Plant Reference**: Plant code must exist in Plant master and be active (not deleted)
6. **Store Type**: Must be one of the valid choices: RAW, SCRAP, BILLET, FG, WIP
7. **Case Sensitivity**: Store codes are case-insensitive for uniqueness check (e.g., "ST001" = "st001")
8. **Duplicate Handling**: If a store with the same code already exists in the database, the import will fail for that row

## Troubleshooting

### Duplicate Store Code Errors
- Store codes must be unique (case-insensitive)
- Check if store already exists in database
- Use different codes for new stores
- The import will fail for duplicate codes within the file and against existing database records

### Invalid Store Type Errors
- Store type must be one of: RAW, SCRAP, BILLET, FG, WIP
- Check error report for exact value provided
- Ensure the value matches one of the valid choices exactly (case-insensitive)

### Invalid Plant Code Errors
- Plant code must exist in Plant master
- Plant must be active (not deleted)
- Check if plant code exists in database
- Verify plant code spelling and case (case-insensitive lookup)

### Validation Errors
- Check error report for detailed messages
- Verify all required fields are present
- Ensure data types match expected format
- Store Code, Store Name, Store Type, and Plant Code fields cannot be empty or null
