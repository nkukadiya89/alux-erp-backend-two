# Department Bulk Import - Test Data

This directory contains test files for testing the Department Master bulk import functionality.

## Files

1. **departments_valid.csv** - Sample CSV file with 25 valid department records
2. **departments_with_errors.csv** - Sample CSV file with intentional errors for testing error handling

## CSV File Format

### Required Columns
- **Department Code** - Unique department code (alphanumeric, will be converted to uppercase)
- **Department Name** - Department name
- **Department Type** - One of: PRODUCTION, STORE, QA, PURCHASE, MAINTENANCE, FINANCE, ADMIN
- **Plant Name** - Plant name (must exist in Plant table, case-insensitive lookup)
- **Status** - Active or Inactive

### Optional Columns
- **Cost Center Code** - Cost center code (max 50 characters)
- **Parent Department Code** - Parent department code (must exist and be in same plant if both have plants)

## Data Format

### Department Code
- Alphanumeric with hyphens/underscores
- Unique (case-insensitive)
- Will be automatically converted to uppercase
- Examples: `DEPT-001`, `DIV-001`, `SEC-001`

### Department Type
Valid values (case-insensitive):
- `PRODUCTION` - Production Department
- `STORE` - Store/Warehouse Department
- `QA` - Quality Assurance Department
- `PURCHASE` - Purchase/Procurement Department
- `MAINTENANCE` - Maintenance Department
- `FINANCE` - Finance/Accounts Department
- `ADMIN` - Administration Department

### Status
- `Active` - Active department
- `Inactive` - Inactive department

### Plant Name
- Must match an existing Plant name in the database
- Case-insensitive lookup (e.g., "Mumbai Extrusion Plant" = "mumbai extrusion plant")
- Required field (cannot be empty/null)
- Plant must exist and not be deleted
- Examples: "Mumbai Extrusion Plant", "Delhi Assembly Unit", "Bangalore Warehouse"

### Parent Department Code
- Must match an existing Department code
- Must be in the same plant (plant is required for all departments)
- Cannot be the same department (self-reference)
- Parent department must not be archived
- Can be empty/null for top-level departments

### Cost Center Code
- Optional field
- Maximum 50 characters
- Can be empty/null

## Expected Results

### departments_valid.csv
- **Total Rows**: 25
- **Success Count**: 25 (assuming all plant codes exist)
- **Error Count**: 0
- **Status**: Completed

**Note**: If some Plant Names don't exist in your database, those rows will fail with "Plant not found" error. Update the Plant Names in the CSV to match your actual plant names (case-insensitive match).

### departments_with_errors.csv
- **Total Rows**: 15
- **Success Count**: 5 (rows 1, 6, 9, 11, 13, 15)
- **Error Count**: 10
- **Status**: Partial Success

### Errors in departments_with_errors.csv:

1. **Row 2**: Duplicate Department Code (DEPT-101) - duplicate within file
2. **Row 3**: Invalid Department Type - "INVALID_TYPE" is not a valid choice
3. **Row 4**: Invalid Plant Name - "Non Existent Plant" does not exist in Plant table
4. **Row 5**: Invalid Status - "InvalidStatus" is not a valid choice (must be Active/Inactive)
5. **Row 6**: Missing Department Name - required field is empty
6. **Row 8**: Invalid Parent Department Code - "INVALID-DEPT" does not exist
7. **Row 9**: Parent in Different Plant - Parent department (DEPT-001) is in PLANT-001, but child is in PLANT-002
8. **Row 12**: Empty Department Code - required field is empty
9. **Row 14**: Invalid Cost Center Format - exceeds 50 character limit

## Testing Workflow

### Step 1: Prepare Test Data
1. Ensure you have Plants in your database with names matching the CSV (e.g., "Mumbai Extrusion Plant", "Delhi Assembly Unit", etc.)
2. If using different plant names, update the CSV files accordingly (case-insensitive match)

### Step 2: Test Dry Run (Recommended First)
1. Use Postman or API client
2. POST to `/api/v1/departments/bulk-import/`
3. Upload `departments_valid.csv`
4. Set `dry_run=true` in form-data
5. Review validation results without saving to database

### Step 3: Import Valid Data
1. POST to `/api/v1/departments/bulk-import/`
2. Upload `departments_valid.csv`
3. Set `dry_run=false` (or omit)
4. Check response for success/error counts
5. Save the `import_log_id` from response

### Step 4: Test Error Handling
1. POST to `/api/v1/departments/bulk-import/`
2. Upload `departments_with_errors.csv`
3. Review error count in response
4. Use the `import_log_id` to view detailed errors

### Step 5: View Import Logs
1. GET `/api/v1/departments/import-logs/`
2. View all import history
3. Copy an `import_log_id` from the response

### Step 6: View Errors
1. GET `/api/v1/departments/{import_log_id}/import-errors/`
2. View detailed error list with row numbers and error messages

### Step 7: Download Error Report
1. GET `/api/v1/departments/{import_log_id}/error-report/download/`
2. Download CSV file with all error details

### Step 8: Verify Imported Data
1. GET `/api/v1/departments/` to see imported departments
2. Verify the data matches your CSV file
3. Check dropdown API: GET `/api/v1/departments/dropdown/`

## Sample Data Description

### departments_valid.csv Contains:

**Production Departments (6):**
- DEPT-001: Production Department (Mumbai Extrusion Plant)
- DEPT-008: Production Line 1 (Delhi Assembly Unit, parent: DEPT-001)
- DEPT-009: Production Line 2 (Delhi Assembly Unit, parent: DEPT-001)
- DEPT-023: Production Department (Hyderabad Extrusion)

**Quality Assurance (4):**
- DEPT-002: Quality Assurance (Mumbai Extrusion Plant)
- DEPT-010: Quality Control Lab (Delhi Assembly Unit, parent: DEPT-002)
- DEPT-019: Regional QA (Chennai Site Office)
- DEPT-024: Quality Assurance (Hyderabad Extrusion)

**Store Departments (4):**
- DEPT-003: Store Department (Mumbai Extrusion Plant)
- DEPT-011: Raw Material Store (Delhi Assembly Unit, parent: DEPT-003)
- DEPT-012: Finished Goods Store (Delhi Assembly Unit, parent: DEPT-003)
- DEPT-020: Regional Store (Chennai Site Office)
- DEPT-025: Store Department (Hyderabad Extrusion)

**Purchase Departments (3):**
- DEPT-004: Purchase Department (Mumbai Extrusion Plant)
- DEPT-013: Procurement Team (Bangalore Warehouse)
- DEPT-021: Regional Purchase (Chennai Site Office)

**Maintenance Departments (3):**
- DEPT-005: Maintenance Department (Mumbai Extrusion Plant)
- DEPT-014: Equipment Maintenance (Bangalore Warehouse, parent: DEPT-005)
- DEPT-022: Regional Maintenance (Chennai Site Office)

**Finance Departments (3):**
- DEPT-006: Finance Department (Mumbai Extrusion Plant)
- DEPT-015: Accounts Payable (Bangalore Warehouse, parent: DEPT-006)
- DEPT-016: Accounts Receivable (Bangalore Warehouse, parent: DEPT-006)

**Admin Departments (3):**
- DEPT-007: Admin Department (Mumbai Extrusion Plant)
- DEPT-017: HR Department (Bangalore Warehouse, parent: DEPT-007)
- DEPT-018: IT Support (Bangalore Warehouse, parent: DEPT-007)

## Important Notes

1. **Plant Names**: Update Plant Names in CSV files to match your actual plant names in the database (case-insensitive)
2. **Hierarchical Structure**: Some departments have parent departments, creating a hierarchical structure
3. **Plant Name Required**: Plant Name is required for all departments - cannot be empty
4. **Case Sensitivity**: Department codes and plant names are case-insensitive (DEPT-001 = dept-001, "Mumbai Extrusion Plant" = "mumbai extrusion plant")
5. **Status Requirement**: All departments in the sample are "Active". Change to "Inactive" if needed

## Troubleshooting

### Plant Name Not Found Errors
- Verify Plant Names exist in your database
- Update CSV file with correct Plant Names (exact match, case-insensitive)
- Check for typos or extra spaces in plant names
- Plant Name is required - cannot be empty

### Parent Department Errors
- Ensure parent department exists before importing child
- Parent and child must be in same plant (if both have plants)
- Import parent departments first, then children

### Duplicate Code Errors
- Department codes must be unique (case-insensitive)
- Check if department already exists in database
- Use different codes for new departments

### Validation Errors
- Check error report for detailed messages
- Verify all required fields are present
- Ensure data types match expected format

