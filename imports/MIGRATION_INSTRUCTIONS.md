# Migration Instructions

## Problem
You're getting this error:
```
relation "import_log" does not exist
```

This means the database tables for the imports app haven't been created yet.

## Solution

Run these commands in your terminal (with virtual environment activated):

```bash
# 1. Create migrations (if not already created)
python manage.py makemigrations imports

# 2. Apply migrations to database
python manage.py migrate imports
```

Or apply all pending migrations:
```bash
python manage.py migrate
```

## Verification

After running migrations, verify the tables were created:

```sql
-- PostgreSQL
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('import_log', 'import_error_row');
```

Or check in Django shell:
```python
python manage.py shell

>>> from imports.models import ImportLog, ImportErrorRow
>>> ImportLog.objects.count()
0
>>> ImportErrorRow.objects.count()
0
```

If no errors occur, the tables are created successfully!

## Troubleshooting

### If makemigrations shows "No changes detected"
- The migration file `0001_initial.py` is already created
- Just run `python manage.py migrate imports`

### If you get permission errors
- Ensure your database user has CREATE TABLE permissions
- Check database connection settings

### If migration fails
- Check database logs for detailed error messages
- Ensure all dependencies are installed
- Verify AUTH_USER_MODEL is correctly set in settings.py

