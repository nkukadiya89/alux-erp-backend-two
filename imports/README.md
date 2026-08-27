# Generic Bulk Import Module

A reusable, generic bulk import system for Django ERP applications. This module provides a complete solution for importing data from Excel/CSV files with validation, error tracking, and reporting.

## Features

- **Generic & Reusable**: Base classes that can be extended for any module
- **Multiple File Formats**: Supports Excel (.xlsx, .xls) and CSV files
- **Comprehensive Validation**: Field-level, reference, and business rule validation
- **Error Tracking**: Detailed error logging with row-level error reports
- **Bulk Operations**: Efficient batch processing for large datasets
- **Transaction Safety**: Atomic transactions ensure data consistency
- **Dry Run Mode**: Validate files without saving to database
- **Import History**: Track all import operations with detailed logs

## Architecture

```
imports/
├── models.py              # ImportLog, ImportErrorRow models
├── utils.py               # Utility functions for data normalization
├── validators/
│   ├── base.py            # Base validator classes
│   ├── field_validators.py    # Field-level validators (string, email, etc.)
│   ├── reference_validators.py  # Foreign key validators
│   └── business_rules.py  # Business rule validators
├── parsers/
│   ├── excel_parser.py    # Excel file parser
│   └── csv_parser.py      # CSV file parser
├── writers/
│   └── bulk_writer.py     # Bulk database writer
├── reports/
│   └── error_report.py    # Error reporting and CSV generation
└── services/
    ├── base_importer.py   # Abstract base importer
    └── plant_importer.py  # Example: Plant Master importer
```

## Quick Start

### 1. Create a Custom Importer

Extend `BaseImporter` for your module:

```python
from imports.services.base_importer import BaseImporter
from imports.validators.field_validators import StringValidator, EmailValidator
from myapp.models import MyModel

class MyModelImporter(BaseImporter):
    MODULE_NAME = "MyModel"
    REQUIRED_COLUMNS = ["Name", "Email", "Code"]
    
    def get_field_mapping(self):
        return {
            "Name": "name",
            "Email": "email",
            "Code": "code",
        }
    
    def get_validators(self):
        return {
            "name": [StringValidator("name", max_length=255, required=True)],
            "email": [EmailValidator("email", required=True)],
            "code": [StringValidator("code", max_length=50, required=True)],
        }
    
    def transform_row_data(self, row_data):
        # Transform file data to model format
        return {
            "name": row_data.get("Name"),
            "email": row_data.get("Email"),
            "code": row_data.get("Code"),
        }
    
    def create_model_instance(self, validated_data):
        return MyModel(**validated_data)
```

### 2. Add API Endpoint

Add import actions to your ViewSet:

```python
from rest_framework.decorators import action
from imports.services.my_model_importer import MyModelImporter

class MyModelViewSet(ModelViewSet):
    # ... existing code ...
    
    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"success": False, "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dry_run = request.data.get('dry_run', False)
        importer = MyModelImporter(file, user=request.user, dry_run=dry_run)
        result = importer.import_data()
        
        return Response(result, status=status.HTTP_200_OK)
```

### 3. Use the API

```bash
# Upload file for import
curl -X POST \
  http://localhost:8000/api/v1/mymodel/bulk-import/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data.xlsx"

# Dry run (validate only)
curl -X POST \
  http://localhost:8000/api/v1/mymodel/bulk-import/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data.xlsx" \
  -F "dry_run=true"
```

## Validators

### Field Validators

- **StringValidator**: Validates string fields with length constraints
- **EmailValidator**: Validates email addresses
- **PhoneValidator**: Validates phone numbers
- **IntegerValidator**: Validates integer fields
- **DecimalValidator**: Validates decimal fields with precision
- **ChoiceValidator**: Validates choice fields against allowed values
- **UniqueValidator**: Validates uniqueness within import file

### Reference Validators

- **ForeignKeyValidator**: Validates foreign key references
- **DatabaseUniqueValidator**: Validates uniqueness against database
- **CustomReferenceValidator**: Custom lookup function validator

### Business Rule Validators

- **CustomBusinessRuleValidator**: Custom validation function
- **ConditionalValidator**: Conditional validation based on other fields
- **CrossFieldValidator**: Validates multiple fields together

## Example: Plant Master Import

The `PlantImporter` demonstrates a complete implementation:

```python
from imports.services.plant_importer import PlantImporter

# In your view
importer = PlantImporter(file, user=request.user)
result = importer.import_data()

# Result structure:
{
    "success": True,
    "message": "Import completed: 100 successful, 5 errors",
    "total_rows": 105,
    "success_count": 100,
    "error_count": 5,
    "import_log_id": "uuid-here"
}
```

## Error Handling

Errors are automatically tracked in the database:

```python
# Get import errors
from imports.models import ImportLog, ImportErrorRow

import_log = ImportLog.objects.get(id=import_log_id)
errors = ImportErrorRow.objects.filter(import_log=import_log)

# Get error summary
from imports.reports.error_report import ErrorReport
error_report = ErrorReport(import_log)
summary = error_report.get_errors_summary()
```

## Database Models

### ImportLog

Tracks import operations:
- `module_name`: Module being imported (e.g., "Plant")
- `file_name`: Original file name
- `status`: pending, processing, completed, failed, partial
- `total_rows`, `success_count`, `error_count`
- `error_summary`: JSON summary of errors

### ImportErrorRow

Tracks individual row errors:
- `import_log`: Foreign key to ImportLog
- `row_number`: Row number in file (1-indexed)
- `error_type`: validation, reference, business_rule, etc.
- `field_name`: Field that caused error
- `error_message`: Error description
- `raw_data`: Original row data (JSON)

## Best Practices

1. **Always validate required columns** in `REQUIRED_COLUMNS`
2. **Use field mapping** to handle different column name variations
3. **Normalize data** in `transform_row_data` (uppercase codes, trim strings, etc.)
4. **Use bulk operations** for performance (default batch size: 1000)
5. **Track unique values** within import file to prevent duplicates
6. **Provide clear error messages** for better user experience
7. **Use dry_run** for testing before actual import
8. **Monitor import logs** for troubleshooting

## Performance Considerations

- Batch size defaults to 1000 records per batch
- Use `bulk_create` for better performance
- Transactions ensure atomicity
- Consider indexing on lookup fields for reference validators
- Cache foreign key lookups when possible

## Migration

After adding the imports app, create migrations:

```bash
python manage.py makemigrations imports
python manage.py migrate
```

## Admin Interface

Import logs and errors are available in Django admin:

- View all import logs
- Filter by module, status, date
- View detailed error rows
- Download error reports

## Extending for Other Modules

To add bulk import for another module:

1. Create a new importer class extending `BaseImporter`
2. Define field mapping and validators
3. Implement `transform_row_data` and `create_model_instance`
4. Add API endpoint to your ViewSet
5. Test with sample data

See `plant_importer.py` for a complete example.

