# Plant Master Load Testing - Implementation Summary

## Files Created

### Core Testing Files
1. **`locustfile.py`** (Root directory)
   - Main Locust test file
   - Implements all 8 Plant Master API endpoints
   - Weighted task distribution (60% list, 15% create, etc.)
   - JWT authentication handling
   - Dynamic plant_id management
   - Response time assertions
   - Error handling and retry logic

### Documentation
2. **`load_testing/README.md`**
   - Comprehensive testing guide
   - Test scenarios (smoke, load, stress, soak)
   - Execution commands
   - Report interpretation
   - Database impact analysis
   - Monitoring guidelines

3. **`load_testing/QUICK_START.md`**
   - Quick reference guide
   - Essential commands
   - Troubleshooting tips

4. **`load_testing/OPTIMIZATION_RECOMMENDATIONS.md`**
   - Database optimization strategies
   - Caching implementation
   - Application-level optimizations
   - Scaling recommendations
   - Performance improvement estimates

### Setup & Utilities
5. **`load_testing/setup_test_users.py`**
   - Script to create test users
   - Handles user creation/update

6. **`load_testing/run_tests.sh`**
   - Bash script for automated test execution
   - Supports all test types (smoke, load, stress, soak)

7. **`load_testing/requirements.txt`**
   - Python dependencies (locust, requests)

## Test Coverage

### API Endpoints Tested
1. ✅ GET `/api/v1/masters/plants/` - List plants (60% weight)
2. ✅ POST `/api/v1/masters/plants/` - Create plant (15% weight)
3. ✅ GET `/api/v1/masters/plants/{id}/` - Retrieve plant (3% weight)
4. ✅ PUT `/api/v1/masters/plants/{id}/` - Full update
5. ✅ PATCH `/api/v1/masters/plants/{id}/` - Partial update (10% weight)
6. ✅ POST `/api/v1/masters/plants/{id}/change-status/` - Change status (5% weight)
7. ✅ DELETE `/api/v1/masters/plants/{id}/` - Soft delete (2% weight)
8. ✅ GET `/api/v1/masters/plants/dropdown/` - Dropdown API (5% weight)

### Test Scenarios
- **Smoke Test**: Minimal load verification
- **Load Test**: Normal expected load (100 users)
- **Stress Test**: Peak load (300 users)
- **Soak Test**: Extended duration (30 minutes)

## Key Features

### Authentication
- JWT token management
- Automatic re-authentication on token expiry
- Multiple test user support

### Realistic Workload
- Weighted task distribution matching ERP usage patterns
- Randomized payloads for realistic data
- Dynamic plant_id tracking per user
- Proper wait times between requests

### Assertions & Validation
- Response time thresholds (< 500ms average, < 800ms 95th percentile)
- Status code validation
- Error rate monitoring (< 1% target)
- Business rule validation (duplicate plant_code handling)

### Reporting
- CSV reports for analysis
- HTML reports for visualization
- Console real-time metrics
- Failure tracking

## Usage Examples

### Basic Usage
```bash
# Install dependencies
pip install -r load_testing/requirements.txt

# Setup test users
python load_testing/setup_test_users.py

# Run interactive test
locust -f locustfile.py --host=http://localhost:8000
```

### Automated Testing
```bash
# Load test with reports
locust -f locustfile.py --host=http://localhost:8000 \
    --headless -u 100 -r 10 -t 10m \
    --csv=reports/load_test \
    --html=reports/load_test.html
```

### Using Shell Script (Linux/Mac)
```bash
./load_testing/run_tests.sh load
./load_testing/run_tests.sh stress
```

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Average Response Time | < 500ms | > 1000ms |
| 95th Percentile | < 800ms | > 2000ms |
| Error Rate | < 1% | > 5% |
| Throughput | > 50 req/s | < 20 req/s |

## Database Impact

### Read/Write Ratio
- **Read Operations**: 60% (List, Retrieve, Dropdown)
- **Write Operations**: 30% (Create, Update, Delete, Status Change)
- **Ratio**: ~2:1 (Read-heavy workload)

### Index Usage
- `plant_code` (unique lookup)
- `status` (filtering)
- `city` (search)
- `deleted, status` (composite filter)

### Expected Load
- **Queries/sec**: 50-100 under peak load
- **Connection Pool**: Monitor for exhaustion
- **Query Performance**: Should use indexes efficiently

## Optimization Opportunities

### Immediate (High Impact)
1. Redis caching for dropdown API (80-90% improvement)
2. Connection pooling with PgBouncer (30-40% improvement)
3. Serializer optimization for list view (20-30% improvement)

### Short-term (Medium Impact)
1. Read replicas for read operations (40-50% load reduction)
2. Query result caching (15-25% improvement)
3. Performance monitoring integration

### Long-term (Scalability)
1. Horizontal scaling (load balancer)
2. APM tools integration
3. Database sharding (if needed)

## Monitoring Checklist

During tests, monitor:
- [ ] Database connection pool usage
- [ ] Query execution times
- [ ] Index usage statistics
- [ ] Memory usage trends
- [ ] CPU utilization
- [ ] Response time percentiles
- [ ] Error rates by endpoint
- [ ] Throughput (requests/sec)

## Next Steps

1. **Run Smoke Test** to verify setup
2. **Run Load Test** to establish baseline
3. **Run Stress Test** to identify breaking point
4. **Analyze Reports** to identify bottlenecks
5. **Implement Optimizations** based on findings
6. **Re-run Tests** to validate improvements

## Support & Resources

- **Locust Documentation**: https://docs.locust.io/
- **Django Performance**: https://docs.djangoproject.com/en/stable/topics/performance/
- **PostgreSQL Tuning**: https://www.postgresql.org/docs/current/performance-tips.html

## Notes

- Tests are designed for **non-production environments**
- Ensure test database has sufficient data (100-500 plants)
- Monitor both application and database metrics
- Run tests during off-peak hours if possible
- Document baseline metrics for comparison

