# Excel/CSV Template Guide

## Plant Master Import Template

### Required Columns

| Column Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| Plant Code | Text | Yes | Unique plant code (alphanumeric, uppercase) | PLANT-001 |
| Plant Name | Text | Yes | Plant name (max 255 chars) | Mumbai Plant |
| Plant Type | Text | Yes | Plant Type code (e.g., EXTRUSION, FABRICATION, WAREHOUSE, SITE, OFFICE). Must exist in PlantType table. Case-insensitive. | EXTRUSION |
| Status | Choice | Yes | Active, Inactive | Active |
| Address Line 1 | Text | Yes | Primary address (max 255 chars) | 123 Main Street |
| Address Line 2 | Text | No | Secondary address (max 255 chars) | Suite 100 |
| City | Text | Yes | City name (max 100 chars) | Mumbai |
| State | Text | Yes | State name (max 100 chars) | Maharashtra |
| Country | Text | Yes | Country name (max 100 chars) | India |
| Postal Code | Text | Yes | Postal/ZIP code (max 20 chars) | 400001 |
| Phone Number | Text | Yes | Phone number (10-20 digits) | 9876543210 |
| Email | Email | Yes | Valid email address | plant@example.com |
| Plant Head Name | Text | Yes | Plant head name (max 255 chars) | John Doe |

### Column Order

Columns can be in any order, but all required columns must be present.

### Data Format Guidelines

1. **Plant Code**:
   - Must be unique (not duplicate in file or database)
   - Alphanumeric with hyphens/underscores allowed
   - Will be converted to uppercase automatically
   - Example: `PLANT-001`, `PLANT_001`, `PLT001`

2. **Plant Type**:
   - Must be a valid Plant Type code that exists in the PlantType table
   - Supported codes: `EXTRUSION`, `FABRICATION`, `WAREHOUSE`, `SITE`, `OFFICE`, `MELTING_CASTING`, `HEAT_TREATMENT`, `ANODIZING`, `POWDER_COATING`, `QUALITY_LAB`
   - Case-insensitive matching (e.g., "extrusion", "EXTRUSION", "Extrusion" all work)
   - Will be normalized to uppercase automatically
   - Must reference an active (not deleted) PlantType record

3. **Status**:
   - Must be exactly: `Active` or `Inactive`
   - Case-insensitive matching

4. **Email**:
   - Must be valid email format
   - Will be converted to lowercase automatically

5. **Phone Number**:
   - Can include formatting (spaces, dashes, parentheses)
   - Will be cleaned automatically
   - Must contain 10-20 digits after cleaning

6. **Dates**:
   - Not required in import (auto-generated)

### Sample Excel Template

```
Plant Code | Plant Name      | Plant Type | Status | Address Line 1    | City    | State       | Country | Postal Code | Phone Number | Email              | Plant Head Name
-----------|-----------------|------------|--------|-------------------|---------|-------------|---------|-------------|--------------|--------------------|----------------
PLANT-001  | Mumbai Plant    | EXTRUSION  | Active | 123 Main Street   | Mumbai  | Maharashtra | India   | 400001      | 9876543210   | plant1@example.com | John Doe
PLANT-002  | Delhi Warehouse| WAREHOUSE  | Active | 456 Park Avenue   | Delhi   | Delhi       | India   | 110001      | 9876543211   | plant2@example.com | Jane Smith
```

### Common Errors

1. **Missing Required Column**: Ensure all required columns are present
2. **Duplicate Plant Code**: Each plant code must be unique in the file
3. **Invalid Email**: Use valid email format
4. **Invalid Phone**: Phone must contain 10-20 digits
5. **Invalid Plant Type**: Plant Type code must exist in PlantType table and be active (not deleted)
6. **Invalid Choice**: Status must match allowed values (Active/Inactive)
6. **Existing Code**: Plant code already exists in database (if not updating)

### Tips

- Use Excel formulas for generating sequential codes
- Validate data in Excel before importing
- Use data validation dropdowns in Excel for choice fields
- Keep a backup of your import file
- Test with a small file first (dry_run mode)
- Review error report after import

### Dry Run

Before importing, use dry_run mode to validate:

```bash
POST /api/v1/masters/plants/bulk-import/
{
    "file": <file>,
    "dry_run": true
}
```

This will validate all rows without saving to database.

