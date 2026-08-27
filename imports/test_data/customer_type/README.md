# Customer Type Bulk Import - Test Data

This directory contains test files for testing the Customer Type Master bulk import functionality.

## Files

1. **customer_type_valid.csv** - Sample CSV file with 20 valid customer type records
2. **customer_types_with_errors.csv** - Sample CSV file with intentional errors for testing error handling

## CSV File Format

### Required Columns
- **Name** - Customer type name (max 255 characters, unique)

## Data Format

### Name
- Customer type name
- Maximum 255 characters
- Must be unique (case-insensitive)
- Required field (cannot be empty/null)
- Examples: "Retail Customer", "Wholesale Customer", "Corporate Customer"

## Expected Results

### customer_type_valid.csv
- **Total Rows**: 20
- **Success Count**: 20 (assuming no duplicates exist in database)
- **Error Count**: 0
- **Status**: Completed

**Note**: If some customer type names already exist in your database, those rows will fail with "duplicate name" error. The import will skip duplicates and create new ones.

### customer_types_with_errors.csv
- **Total Rows**: 7
- **Success Count**: 5 (rows 1, 4, 5, 6, 7)
- **Error Count**: 2
- **Status**: Partial Success

### Errors in customer_types_with_errors.csv:

1. **Row 2**: Duplicate Name - "Valid Customer Type 1" is duplicated within the file (row 1 and row 2)
2. **Row 3**: Name Too Long - Name exceeds 255 character limit

## Testing Workflow

### Step 1: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/customer-types/bulk-import/`
3. Upload `customer_type_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 2: Import Valid Data
1. POST to `/api/v1/customer-types/bulk-import/`
2. Upload `customer_type_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

### Step 3: Test Error Handling
1. POST to `/api/v1/customer-types/bulk-import/`
2. Upload `customer_types_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

### Step 4: View Import Logs
1. GET `/api/v1/customer-types/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 5: View Errors
1. GET `/api/v1/customer-types/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 6: Download Error Report
1. GET `/api/v1/customer-types/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 7: Verify Imported Data
1. GET `/api/v1/customer-types/` to see imported customer types
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/customer-types/dropdown/`

## Sample Data Description

### customer_type_valid.csv Contains:

**20 Customer Types:**
- Retail Customer
- Wholesale Customer
- Corporate Customer
- Government Customer
- Export Customer
- OEM Customer
- Distributor
- Dealer
- Franchise
- Institutional Customer
- Direct Customer
- Online Customer
- B2B Customer
- B2C Customer
- VIP Customer
- Preferred Customer
- Standard Customer
- Premium Customer
- Enterprise Customer
- Small Business Customer

## Important Notes

1. **Name Uniqueness**: Customer type names must be unique (case-insensitive)
2. **Name Length**: Maximum 255 characters
3. **Required Field**: Name is required and cannot be empty
4. **Case Sensitivity**: Names are case-insensitive for uniqueness check (e.g., "Retail Customer" = "retail customer")
5. **Duplicate Handling**: If a customer type with the same name already exists in the database, the import will fail for that row

## Troubleshooting

### Duplicate Name Errors
- Customer type names must be unique (case-insensitive)
- Check if customer type already exists in database
- Use different names for new customer types
- The import will fail for duplicate names within the file and against existing database records

### Name Too Long Errors
- Customer type names must be 255 characters or less
- Check error report for exact character count
- Shorten names that exceed the limit

### Validation Errors
- Check error report for detailed messages
- Verify all required fields are present
- Ensure data types match expected format
- Name field cannot be empty or null
