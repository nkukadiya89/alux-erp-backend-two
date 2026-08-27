# Postman Setup Guide - Plant Bulk Import

## Quick Start

### 1. Import Collection
1. Open Postman
2. Click **Import** (top left)
3. Select `Plant_Bulk_Import.postman_collection.json`
4. Collection imported! ✅

### 2. Set Environment Variables

Create a new environment or use default:

| Variable | Initial Value | Description |
|----------|--------------|-------------|
| `base_url` | `http://localhost:8000` | Your Django server URL |
| `jwt_token` | (empty) | Auto-filled after login |
| `import_log_id` | (empty) | Auto-filled after import |

**To set variables:**
1. Click **Environments** (left sidebar)
2. Click **+** to create new or edit existing
3. Add variables above
4. Click **Save**

### 3. Update Login Credentials

1. Open **Authentication > Login - Get JWT Token**
2. Go to **Body** tab
3. Update email and password:
```json
{
    "email": "your-email@example.com",
    "password": "your-password",
    "keep_me_logged_in": true
}
```

## Testing Steps

### 🔐 Step 1: Login
1. Select **Login - Get JWT Token** request
2. Click **Send**
3. ✅ Token automatically saved to `jwt_token` variable
4. Check response - should see `"success": true`

### 🧪 Step 2: Dry Run Test (Recommended)
1. Select **Bulk Import Plants (Dry Run - Validate Only)**
2. In **Body** tab, click **Select Files** for `file` field
3. Choose `plants_with_errors.csv`
4. Ensure `dry_run` = `true`
5. Click **Send**
6. ✅ Review validation results (no data saved)

### ✅ Step 3: Import Valid Data
1. Select **Bulk Import Plants (Valid Data)**
2. In **Body** tab, click **Select Files** for `file` field
3. Choose `plants_valid.csv`
4. Ensure `dry_run` = `false`
5. Click **Send**
6. ✅ Check response:
   - `success_count`: 10
   - `error_count`: 0
   - `import_log_id`: saved automatically

### ❌ Step 4: Test Error Handling
1. Select **Bulk Import Plants (With Errors)**
2. In **Body** tab, select `plants_with_errors.csv`
3. Click **Send**
4. ✅ Check response:
   - `success_count`: 4
   - `error_count`: 6
   - `import_log_id`: saved automatically

### 📋 Step 5: View Import Logs
1. Select **Get Import Logs**
2. Click **Send**
3. ✅ See all import history
4. Copy an `import_log_id` from response

### 🔍 Step 6: View Errors
1. Select **Get Import Errors**
2. Replace `{{import_log_id}}` in URL with actual ID (or use saved variable)
3. Click **Send**
4. ✅ See detailed error list with:
   - Row numbers
   - Error types
   - Field names
   - Error messages
   - Raw data

### 📥 Step 7: Download Error Report
1. Select **Download Error Report (CSV)**
2. Replace `{{import_log_id}}` if needed
3. Click **Send**
4. ✅ CSV file downloads automatically

### ✅ Step 8: Verify Imported Data
1. Select **List Plants**
2. Click **Send**
3. ✅ See imported plants in response

## File Upload in Postman

### For CSV Files:
1. Go to **Body** tab
2. Select **form-data**
3. Find `file` field
4. Change type from **Text** to **File** (dropdown on right)
5. Click **Select Files**
6. Choose your CSV file

### For Excel Files:
Same process as CSV - Postman supports both!

## Expected Responses

### Successful Import
```json
{
    "success": true,
    "message": "Import completed: 10 successful, 0 errors",
    "data": {
        "total_rows": 10,
        "success_count": 10,
        "error_count": 0,
        "import_log_id": "uuid-here"
    }
}
```

### Import with Errors
```json
{
    "success": false,
    "message": "Import completed: 4 successful, 6 errors",
    "data": {
        "total_rows": 10,
        "success_count": 4,
        "error_count": 6,
        "import_log_id": "uuid-here"
    }
}
```

### Import Logs Response
```json
{
    "success": true,
    "data": [
        {
            "id": "uuid",
            "file_name": "plants_valid.csv",
            "status": "completed",
            "total_rows": 10,
            "success_count": 10,
            "error_count": 0,
            "success_rate": 100.0,
            "started_at": "2024-01-01T10:00:00Z",
            "completed_at": "2024-01-01T10:00:05Z"
        }
    ],
    "count": 1,
    "page": 1,
    "page_size": 20
}
```

### Import Errors Response
```json
{
    "success": true,
    "data": {
        "summary": {
            "total_errors": 6,
            "by_type": {
                "validation": 5,
                "duplicate": 1
            },
            "by_field": {
                "email": 1,
                "phone_number": 2,
                "plant_code": 1
            }
        },
        "errors": [
            {
                "row_number": 2,
                "error_type": "duplicate",
                "field_name": "plant_code",
                "error_message": "plant_code 'PLANT-101' is duplicated in the import file",
                "raw_data": {...}
            }
        ]
    }
}
```

## Troubleshooting

### ❌ "No file provided"
- Ensure file field is set to **File** type (not Text)
- File must be selected

### ❌ "Unauthorized" or 401
- Run **Login** request first
- Check JWT token is saved in environment
- Token may have expired (check expiry time)

### ❌ "Invalid file type"
- Use CSV (.csv) or Excel (.xlsx, .xls) files only
- Check file extension

### ❌ "Missing required columns"
- Check CSV has all required columns
- Column names must match exactly (case-sensitive)
- See `TEMPLATE_GUIDE.md` for required columns

### ❌ Connection Error
- Verify `base_url` is correct
- Check Django server is running
- Test with: `http://localhost:8000/api/v1/plants/`

## Tips

1. **Always test with dry_run first** - validates without saving
2. **Use small test files** - easier to debug
3. **Check import logs** - track all imports
4. **Review error reports** - fix data issues
5. **Verify imported data** - use List Plants endpoint

## Collection Structure

```
Plant Bulk Import API
├── Authentication
│   └── Login - Get JWT Token
├── Plant Bulk Import
│   ├── Bulk Import Plants (Valid Data)
│   ├── Bulk Import Plants (Dry Run - Validate Only)
│   └── Bulk Import Plants (With Errors)
├── Import Logs & Errors
│   ├── Get Import Logs
│   ├── Get Import Errors
│   └── Download Error Report (CSV)
└── Plant CRUD (Reference)
    └── List Plants
```

## Next Steps

After successful testing:
1. Create your own CSV files with real data
2. Use the same endpoints for production imports
3. Monitor import logs regularly
4. Review error reports to improve data quality

Happy Testing! 🚀

