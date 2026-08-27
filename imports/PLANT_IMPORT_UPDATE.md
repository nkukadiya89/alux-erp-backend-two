# Plant Import Feature Update

## Overview
Updated the Plant Master bulk import feature to handle the new Plant Capability architecture where `plant_type` is now a ForeignKey to `PlantType` instead of a CharField with choices.

## Changes Made

### 1. Updated Imports
- Added `PlantType` model import
- Added `ForeignKeyValidator` import for validating foreign key references

### 2. Updated Validators
- **Before**: Used `ChoiceValidator` with `Plant.PLANT_TYPE_CHOICES` (which no longer exists)
- **After**: Uses `ForeignKeyValidator` to validate that the plant_type code exists in the `PlantType` table
  - Validates by `code` field (case-insensitive)
  - Ensures the PlantType is not deleted (`is_deleted=False`)

### 3. Updated Data Transformation
- **Before**: Normalized plant_type as a choice string value
- **After**: 
  - Looks up `PlantType` instance by code (case-insensitive)
  - Caches PlantType lookups for performance
  - Converts plant_type code to PlantType instance (ForeignKey object)
  - Handles missing PlantType gracefully (sets to None, validation will catch)

### 4. Added Caching
- Added `plant_type_cache` to cache PlantType lookups during import
- Improves performance when importing multiple plants with the same plant_type

## CSV/Excel File Format

The import file format remains the same. Users should provide **Plant Type Code** (e.g., "EXTRUSION", "WAREHOUSE", "OFFICE") in the "Plant Type" column.

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

**Note**: The code matching is case-insensitive (e.g., "extrusion", "EXTRUSION", "Extrusion" all work)

## Example CSV/Excel Format

```csv
Plant Code,Plant Name,Plant Type,Status,Address Line 1,City,State,Country,Postal Code,Phone Number,Email,Plant Head Name
PLANT-001,Mumbai Plant,EXTRUSION,Active,123 Industrial Area,Mumbai,Maharashtra,India,400001,9876543210,plant@example.com,John Doe
PLANT-002,Delhi Warehouse,WAREHOUSE,Active,456 Storage St,Delhi,Delhi,India,110001,9876543211,warehouse@example.com,Jane Smith
```

## Validation

The import will validate:
1. ✅ Plant Type code exists in PlantType table
2. ✅ Plant Type is active (not deleted)
3. ✅ Case-insensitive matching (accepts "extrusion", "EXTRUSION", etc.)
4. ✅ All other existing validations (plant_code uniqueness, email format, etc.)

## Error Handling

If a Plant Type code is not found:
- The row will be marked as invalid
- Error message: `"plant_type 'INVALID_CODE' does not exist"`
- The error will be recorded in `ImportErrorRow` with error_type="reference"

## Migration Notes

- Existing import files with old plant_type values (like "Extrusion", "Assembly") will need to be updated to use the new codes (like "EXTRUSION", "FABRICATION")
- The importer automatically normalizes codes to uppercase
- PlantType records should be created before importing plants (via migration 0010_default_plant_capabilities.py)

## Testing

To test the updated import:

1. Ensure PlantType records exist:
   ```python
   from common.models import PlantType
   PlantType.objects.all()  # Should return plant types
   ```

2. Create a test CSV with valid Plant Type codes

3. Use the bulk import API:
   ```bash
   POST /api/v1/plants/bulk-import/
   Content-Type: multipart/form-data
   file: plants.csv
   ```

4. Check import results and error logs



