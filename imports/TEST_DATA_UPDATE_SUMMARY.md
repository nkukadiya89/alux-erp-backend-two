# Test Data Update Summary

## Overview
All test data files and documentation have been updated to work with the new Plant Capability architecture where `plant_type` is now a ForeignKey to `PlantType` instead of a CharField with choices.

## Files Updated

### 1. CSV Test Files

#### ✅ `imports/test_data/plants_valid.csv`
- **Updated**: All plant_type values changed to new codes
- **Old format**: `Extrusion`, `Assembly`, `Warehouse`, `Site`, `Office`
- **New format**: `EXTRUSION`, `FABRICATION`, `WAREHOUSE`, `SITE`, `OFFICE`
- **Status**: Ready for testing ✅

#### ✅ `imports/test_data/plants_with_errors.csv`
- **Updated**: Valid plant types changed to new codes
- **Error test**: Row 5 still has `INVALID_TYPE` to test invalid plant type validation
- **Status**: Ready for testing ✅

### 2. Documentation Files

#### ✅ `imports/test_data/README.md`
- Added section on supported Plant Type codes
- Updated error descriptions
- Added note about case-insensitive matching

#### ✅ `imports/TEMPLATE_GUIDE.md`
- Updated Plant Type column description
- Changed from "Choice" to "Text" with reference to PlantType table
- Updated examples with new codes
- Added validation notes

#### ✅ `imports/test_data/PLANT_TYPE_CODES.md` (NEW)
- Quick reference guide for Plant Type codes
- Migration guide from old format
- Validation information
- Examples

## Plant Type Code Mapping

| Old Value | New Code | Notes |
|-----------|----------|-------|
| `Extrusion` | `EXTRUSION` | Case-insensitive |
| `Assembly` | `FABRICATION` | New name for assembly |
| `Warehouse` | `WAREHOUSE` | Same |
| `Site` | `SITE` | Same |
| `Office` | `OFFICE` | Same |

## Additional Plant Type Codes Available

These codes are also available (created by migration):
- `MELTING_CASTING` - Melting / Casting Plant
- `HEAT_TREATMENT` - Heat Treatment / Ageing Plant
- `ANODIZING` - Anodizing Plant
- `POWDER_COATING` - Powder Coating Plant
- `QUALITY_LAB` - Quality Control / Testing Lab

## Testing Instructions

### 1. Verify PlantType Records Exist

Before testing, ensure PlantType records are created:

```bash
# Run migrations (if not already done)
python manage.py migrate common
```

Or check via Django shell:
```python
from common.models import PlantType
PlantType.objects.all()  # Should return plant types
```

### 2. Test with Valid Data

1. Use `plants_valid.csv` file
2. Import via API:
   ```bash
   POST /api/v1/plants/bulk-import/
   Content-Type: multipart/form-data
   file: plants_valid.csv
   ```
3. Expected result:
   - ✅ 10 rows processed
   - ✅ 10 successful
   - ✅ 0 errors

### 3. Test Error Handling

1. Use `plants_with_errors.csv` file
2. Import via API
3. Expected errors:
   - Row 2: Duplicate Plant Code
   - Row 3: Invalid Email
   - Row 4: Invalid Phone
   - Row 5: **Invalid Plant Type** (INVALID_TYPE doesn't exist)
   - Row 6: Missing Address Line 1
   - Row 7: Invalid Status
   - Row 9: Invalid Phone

### 4. Test Case-Insensitive Matching

You can test that the importer accepts different cases:
- `extrusion` ✅
- `EXTRUSION` ✅
- `Extrusion` ✅
- `ExTrUsIoN` ✅

All will be normalized to `EXTRUSION` and matched to the PlantType record.

## Quick Test Commands

### Using Postman
1. Import `Plant_Bulk_Import.postman_collection.json`
2. Login to get JWT token
3. Use "Bulk Import Plants (Valid Data)" request
4. Select `plants_valid.csv` file
5. Send request

### Using cURL
```bash
# Login first to get token
curl -X POST http://localhost:8000/get-token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}'

# Import plants
curl -X POST http://localhost:8000/api/v1/plants/bulk-import/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@imports/test_data/plants_valid.csv"
```

### Using Django Management Command
```bash
python manage.py debug_plant_import
```

## Validation Details

The import now validates:
1. ✅ Plant Type code exists in PlantType table
2. ✅ Plant Type is active (not deleted)
3. ✅ Case-insensitive code matching
4. ✅ All other existing validations (email, phone, etc.)

## Error Messages

If Plant Type is invalid, you'll see:
```
plant_type 'INVALID_CODE' does not exist
```

This error will be:
- Recorded in `ImportErrorRow` table
- Included in error report
- Shown in import response

## Next Steps

1. ✅ Test files updated
2. ✅ Documentation updated
3. ✅ Ready for testing
4. ⏭️ Test the import feature
5. ⏭️ Verify imported plants have correct PlantType FK

## Support

For questions or issues:
- Check `imports/PLANT_IMPORT_UPDATE.md` for technical details
- Check `imports/test_data/PLANT_TYPE_CODES.md` for code reference
- Review error logs via API: `GET /api/v1/plants/{import_log_id}/import-errors/`



