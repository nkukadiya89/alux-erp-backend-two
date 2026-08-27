# Item Category Module - Database Stress Testing Guide

## Overview

This guide provides instructions for running database stress tests on the Item Category module with 10,000+ records to validate performance under load.

## Prerequisites

- Django project set up and running
- Database with sufficient space for 10,000+ test records
- Python environment activated

## Stress Test Script

**Location:** `tests/stress_test_item_category.py`

### Features

1. **Bulk Data Creation**: Creates 10,000 test categories with various item types
2. **List Performance Testing**: Tests list API with filters, search, and pagination
3. **Dropdown Performance Testing**: Tests dropdown API performance
4. **Pagination Testing**: Tests different page sizes (10, 50, 100, 500)
5. **Bulk Operations Testing**: Tests bulk archive/restore performance
6. **Query Analysis**: Tracks query count and execution time

## Running Stress Tests

### Option 1: Interactive Mode

```bash
python tests/stress_test_item_category.py
```

The script will:
1. Check current ItemCategory count
2. Ask if you want to create 10,000 test categories
3. Run all performance tests
4. Ask if you want to clean up test data

### Option 2: Programmatic Mode

```python
from tests.stress_test_item_category import (
    create_test_categories,
    test_list_performance,
    test_dropdown_performance,
    test_pagination_performance,
    test_bulk_operations_performance,
    cleanup_test_data
)

# Create test data
create_test_categories(10000)

# Run tests
test_list_performance()
test_dropdown_performance()
test_pagination_performance()
test_bulk_operations_performance()

# Cleanup
cleanup_test_data()
```

## Expected Performance Metrics

### List API
- **Target**: < 300ms for 100 records
- **Queries**: 2-3 queries (with select_related)
- **Page sizes**: 10, 50, 100, 500 all should be < 300ms

### Dropdown API
- **Target**: < 100ms (with caching)
- **Queries**: 1 query
- **With filter**: < 150ms

### Bulk Operations
- **Bulk Archive (100 records)**: < 50ms
- **Bulk Restore (100 records)**: < 50ms

## Monitoring

The stress test script logs:
- Execution time per operation
- Number of database queries
- Average time per query
- Progress percentage for bulk operations

## Cleanup

After testing, run cleanup to remove test data:

```python
from tests.stress_test_item_category import cleanup_test_data
cleanup_test_data()
```

Or use the interactive script which offers cleanup option.

## Notes

- Test categories are prefixed with "STRESS-" for easy identification
- All test categories are created with `is_archived=False` and `is_active=True`
- Test data uses various item types (RAW, CONSUMABLE, SEMI, FG, SPARE, SCRAP, TOOLING)
- The script uses bulk_create for efficient data insertion

## Troubleshooting

**Issue**: "No test categories found"
- **Solution**: Run `create_test_categories()` first

**Issue**: Database connection errors
- **Solution**: Ensure database is running and accessible

**Issue**: Memory errors with large datasets
- **Solution**: Process in smaller batches or increase server memory

