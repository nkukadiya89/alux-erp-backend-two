# Plant Type Codes Reference

## Quick Reference

When importing plants via CSV/Excel, use these **Plant Type Codes** in the "Plant Type" column:

| Code | Name | Description |
|------|------|-------------|
| `EXTRUSION` | Extrusion Plant | Manufacturing plant for extrusion operations |
| `FABRICATION` | Fabrication / Assembly Plant | Plant for fabrication and assembly operations |
| `WAREHOUSE` | Warehouse / Dispatch Center | Storage and dispatch facility |
| `SITE` | Project / Site | Project site or construction site |
| `OFFICE` | Corporate Office | Corporate or administrative office |
| `MELTING_CASTING` | Melting / Casting Plant | Plant for melting and casting operations |
| `HEAT_TREATMENT` | Heat Treatment / Ageing Plant | Plant for heat treatment and ageing |
| `ANODIZING` | Anodizing Plant | Plant for anodizing operations |
| `POWDER_COATING` | Powder Coating Plant | Plant for powder coating operations |
| `QUALITY_LAB` | Quality Control / Testing Lab | Quality control and testing laboratory |

## Important Notes

1. **Case-Insensitive**: You can use any case (e.g., "extrusion", "EXTRUSION", "Extrusion")
2. **Auto-Uppercase**: Codes are automatically converted to uppercase during import
3. **Must Exist**: The Plant Type code must exist in the PlantType table
4. **Must Be Active**: The Plant Type must not be deleted (`is_deleted=False`)

## Examples in CSV

```csv
Plant Code,Plant Name,Plant Type,Status,...
PLANT-001,Mumbai Plant,EXTRUSION,Active,...
PLANT-002,Delhi Warehouse,WAREHOUSE,Active,...
PLANT-003,Corporate HQ,OFFICE,Active,...
```

## Migration from Old Format

If you have old CSV files with these values:
- `Extrusion` → Use `EXTRUSION`
- `Assembly` → Use `FABRICATION`
- `Warehouse` → Use `WAREHOUSE`
- `Site` → Use `SITE`
- `Office` → Use `OFFICE`

## Validation

The import will validate:
- ✅ Plant Type code exists in PlantType table
- ✅ Plant Type is active (not deleted)
- ✅ Case-insensitive matching

If validation fails, you'll see an error like:
```
plant_type 'INVALID_CODE' does not exist
```

## Checking Available Plant Types

To see all available Plant Types in your system:

```python
from common.models import PlantType

# Get all active plant types
plant_types = PlantType.objects.filter(is_deleted=False)
for pt in plant_types:
    print(f"{pt.code} - {pt.name}")
```

Or use the API:
```
GET /api/v1/masters/plant-types/
```



