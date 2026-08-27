# Git Commit Guide - Load Testing Files

## Files to COMMIT ✅

These files are part of the codebase and should be committed:

### Source Files
- ✅ `locustfile.py` - Main Locust test file (root directory)
- ✅ `load_testing/` - Entire folder with:
  - ✅ `README.md` - Documentation
  - ✅ `QUICK_START.md` - Quick reference
  - ✅ `OPTIMIZATION_RECOMMENDATIONS.md` - Performance guide
  - ✅ `IMPLEMENTATION_SUMMARY.md` - Implementation overview
  - ✅ `setup_test_users.py` - Test user creation script
  - ✅ `run_tests.sh` - Test execution script
  - ✅ `requirements.txt` - Python dependencies
  - ✅ `.gitkeep` - Ensures folder is tracked

## Files to IGNORE ❌

These are generated artifacts and should NOT be committed:

### Generated Reports
- ❌ `reports/` - Entire directory (ignored via .gitignore)
  - ❌ `*_test_stats.csv` - Statistics CSV files
  - ❌ `*_test_stats_history.csv` - Time-series data
  - ❌ `*_test_failures.csv` - Failure details
  - ❌ `*_test.html` - HTML reports

### Locust Data
- ❌ `.locust/` - Locust internal data files

## .gitignore Configuration

The following entries have been added to `.gitignore`:

```gitignore
# Load Testing Reports (generated artifacts - ignore these)
reports/
reports/**/*.csv
reports/**/*.html

# Locust data files
.locust/
```

## Commit Command

To commit the load testing files:

```bash
# Add all load testing source files
git add locustfile.py
git add load_testing/
git add .gitignore

# Commit
git commit -m "Add Plant Master load testing suite with Locust"
```

## Verification

After committing, verify that reports are ignored:

```bash
# Create a test report
mkdir -p reports
touch reports/test_stats.csv

# Check git status (should NOT show reports/)
git status

# Reports should be ignored, source files should be tracked
```

## Notes

- **Source files** (locustfile.py, load_testing/*.py, *.md, *.sh) are **part of the codebase** and should be version controlled
- **Generated reports** (CSV, HTML in reports/) are **temporary artifacts** and should be ignored
- Each developer can generate their own reports locally
- Reports can be regenerated anytime by running the tests

