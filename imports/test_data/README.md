# Plant Bulk Import - Test Data & Postman Collection

This directory contains test files and Postman collection for testing the Plant Master bulk import functionality.

## Files

1. **plants_valid.csv** - Sample CSV file with 10 valid plant records
2. **plants_with_errors.csv** - Sample CSV file with intentional errors for testing error handling
3. **Plant_Bulk_Import.postman_collection.json** - Complete Postman collection with all endpoints

## Setup Instructions

### 1. Import Postman Collection

1. Open Postman
2. Click **Import** button
3. Select `Plant_Bulk_Import.postman_collection.json`
4. Collection will be imported with all endpoints

### 2. Configure Environment Variables

Create a new environment in Postman or use the default one:

- **base_url**: `http://localhost:8000` (or your server URL)
- **jwt_token**: Will be auto-populated after login
- **import_log_id**: Will be auto-populated after import

### 3. Update Login Credentials

In the **Login - Get JWT Token** request, update the email and password:
```json
{
    "email": "your-email@example.com",
    "password": "your-password",
    "keep_me_logged_in": true
}
```

### 4. Upload Test Files

When using the bulk import requests:
1. Click on the request
2. Go to **Body** tab
3. Select **form-data**
4. For the `file` field, click **Select Files** and choose:
   - `plants_valid.csv` for valid data test
   - `plants_with_errors.csv` for error handling test

## Testing Workflow

### Step 1: Authenticate
1. Run **Login - Get JWT Token** request
2. Token will be automatically saved to environment variable

### Step 2: Test Dry Run (Recommended First)
1. Run **Bulk Import Plants (Dry Run - Validate Only)**
2. Review the response to see validation results
3. No data will be saved to database

### Step 3: Import Valid Data
1. Run **Bulk Import Plants (Valid Data)**
2. Check response for success/error counts
3. Import log ID will be saved automatically

### Step 4: Test Error Handling
1. Run **Bulk Import Plants (With Errors)**
2. Review error count in response
3. Use the import_log_id to view detailed errors

### Step 5: View Import Logs
1. Run **Get Import Logs** to see all import history
2. Copy an import_log_id from the response

### Step 6: View Errors
1. Update `import_log_id` variable or use the one from Step 3/4
2. Run **Get Import Errors** to see detailed error list
3. Run **Download Error Report (CSV)** to download error report

### Step 7: Verify Imported Data
1. Run **List Plants** to see imported plants
2. Verify the data matches your CSV file

## Expected Results

### plants_valid.csv
- **Total Rows**: 10
- **Success Count**: 10
- **Error Count**: 0
- **Status**: Completed

### plants_with_errors.csv
- **Total Rows**: 10
- **Success Count**: 4 (rows 1, 6, 8, 9)
- **Error Count**: 6
- **Status**: Partial Success

### Errors in plants_with_errors.csv:
1. Row 2: Duplicate Plant Code (PLANT-101) - duplicate within file
2. Row 3: Invalid Email format - "invalid-email" is not a valid email
3. Row 4: Invalid Phone (too short) - "12345" has less than 10 digits
4. Row 5: Invalid Plant Type - "INVALID_TYPE" does not exist in PlantType table
5. Row 6: Missing Address Line 1 - required field is empty
6. Row 7: Invalid Status - "InvalidStatus" is not a valid choice (must be Active/Inactive)
7. Row 9: Invalid Phone (too short) - "123" has less than 10 digits

## API Endpoints

### Bulk Import
- **POST** `/api/v1/plants/bulk-import/`
  - Body: `file` (multipart/form-data)
  - Optional: `dry_run` (boolean)

### Import Logs
- **GET** `/api/v1/plants/import-logs/`
  - Query params: `page`, `page_size`

### Import Errors
- **GET** `/api/v1/plants/{import_log_id}/import-errors/`

### Download Error Report
- **GET** `/api/v1/plants/{import_log_id}/download-error-report/`

## Troubleshooting

### Authentication Issues
- Ensure you've run the Login request first
- Check that JWT token is saved in environment variable
- Token expires after 360 days (check settings)

### File Upload Issues
- Ensure file is selected in form-data
- Check file format (CSV or Excel)
- Verify column names match required format

### Import Errors
- Check error details using Get Import Errors endpoint
- Review CSV file format and data types
- Ensure all required columns are present

### Server Connection
- Verify `base_url` is correct
- Check if Django server is running
- Ensure CORS is configured if testing from browser

## CSV File Format

### Required Columns
- Plant Code
- Plant Name
- Plant Type
- Status
- Address Line 1
- City
- State
- Country
- Postal Code
- Phone Number
- Email
- Plant Head Name

### Optional Columns
- Address Line 2

### Data Format
- **Plant Code**: Alphanumeric, unique, will be converted to uppercase
- **Plant Type**: Plant Type code (e.g., EXTRUSION, FABRICATION, WAREHOUSE, SITE, OFFICE). Must exist in PlantType table. Case-insensitive.
- **Status**: Active or Inactive
- **Email**: Valid email format
- **Phone**: 10-20 digits (formatting will be removed)

### Supported Plant Type Codes
- `EXTRUSION` - Extrusion Plant
- `FABRICATION` - Fabrication / Assembly Plant
- `WAREHOUSE` - Warehouse / Dispatch Center
- `SITE` - Project / Site
- `OFFICE` - Corporate Office
- `MELTING_CASTING` - Melting / Casting Plant
- `HEAT_TREATMENT` - Heat Treatment / Ageing Plant
- `ANODIZING` - Anodizing Plant
- `POWDER_COATING` - Powder Coating Plant
- `QUALITY_LAB` - Quality Control / Testing Lab

**Note**: Plant Type codes are case-insensitive (e.g., "extrusion", "EXTRUSION", "Extrusion" all work)

See `imports/TEMPLATE_GUIDE.md` for detailed format requirements.

