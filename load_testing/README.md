# Plant Master API - Load & Stress Testing Guide

## Overview
Comprehensive load testing suite for Plant Master APIs using Locust. This suite validates performance, scalability, and stability under various load conditions.

## Prerequisites

### 1. Install Locust
```bash
pip install locust
```

### 2. Create Test Users
Before running tests, create test users in your database:

```python
# Run in Django shell: python manage.py shell
from user.models import User

test_users = [
    {"email": "loadtest1@example.com", "password": "TestPass123!"},
    {"email": "loadtest2@example.com", "password": "TestPass123!"},
    {"email": "loadtest3@example.com", "password": "TestPass123!"},
    {"email": "loadtest4@example.com", "password": "TestPass123!"},
    {"email": "loadtest5@example.com", "password": "TestPass123!"},
]

for user_data in test_users:
    user = User.objects.create_user(
        email=user_data["email"],
        password=user_data["password"],
        first_name="Load",
        last_name="Test",
        is_active=True
    )
    print(f"Created user: {user.email}")
```

### 3. Database Setup
Ensure your test database has sufficient data:
- At least 100-500 existing plant records for realistic testing
- Proper indexes (already created in migration)

## Test Scenarios

### 1. Smoke Test
**Purpose**: Verify all APIs respond under minimal load

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 5 -r 1 -t 2m
```

**Expected Results**:
- All endpoints respond with 200/201 status
- No failures
- Response times < 1s

### 2. Load Test
**Purpose**: Validate performance under expected load

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 10m --csv=reports/load_test
```

**Success Criteria**:
- Average response time < 500ms
- 95th percentile < 800ms
- Error rate < 1%
- Throughput > 50 requests/sec

### 3. Stress Test
**Purpose**: Identify breaking point and maximum capacity

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 300 -r 10 -t 20m --csv=reports/stress_test
```

**Monitor**:
- Response time degradation
- Error rate increase
- Database connection pool exhaustion
- Memory usage

### 4. Soak Test
**Purpose**: Detect memory leaks and stability issues

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 150 -r 5 -t 30m --csv=reports/soak_test
```

**Monitor**:
- Memory growth over time
- Database connection leaks
- Response time stability

## Execution Commands

### Web UI Mode (Interactive)
```bash
locust -f locustfile.py --host=http://localhost:8000
```
Then open: http://localhost:8089

### Headless Mode (Automated)
```bash
# Basic headless run
locust -f locustfile.py --host=http://localhost:8000 --headless -u 300 -r 10 -t 20m

# With CSV reports
locust -f locustfile.py --host=http://localhost:8000 --headless -u 300 -r 10 -t 20m \
    --csv=reports/plant_load_test

# With HTML report
locust -f locustfile.py --host=http://localhost:8000 --headless -u 300 -r 10 -t 20m \
    --html=reports/plant_load_test.html

# Combined (CSV + HTML)
locust -f locustfile.py --host=http://localhost:8000 --headless -u 300 -r 10 -t 20m \
    --csv=reports/plant_load_test \
    --html=reports/plant_load_test.html
```

### Parameters Explained
- `-u 300`: 300 concurrent users
- `-r 10`: Spawn rate of 10 users per second
- `-t 20m`: Test duration of 20 minutes
- `--csv`: Generate CSV reports
- `--html`: Generate HTML report

## Report Interpretation

### Key Metrics

#### Response Times
- **Average**: Should be < 500ms for load test
- **95th Percentile**: Should be < 800ms
- **99th Percentile**: Should be < 1500ms
- **Max**: Monitor for outliers

#### Request Rates
- **Total Requests**: Total API calls made
- **Requests/sec**: Throughput (higher is better)
- **Failures**: Should be < 1% of total

#### Status Codes
- **200/201**: Success
- **400**: Validation errors (acceptable for duplicate plant_code)
- **401**: Authentication failures (should be minimal)
- **500**: Server errors (should be 0)

### CSV Report Files
- `plant_load_test_stats.csv`: Overall statistics
- `plant_load_test_stats_history.csv`: Time-series data
- `plant_load_test_failures.csv`: Failure details

### HTML Report
Open `plant_load_test.html` in browser for:
- Interactive charts
- Request breakdown by endpoint
- Response time distributions
- Failure analysis

## Database Impact Analysis

### Expected Load Patterns

#### Read Operations (60% of traffic)
- **List Plants**: Most frequent operation
- **Impact**: Heavy on SELECT queries with filters
- **Indexes Used**: 
  - `plant_code` (unique lookup)
  - `status` (filtering)
  - `city` (search)
  - `deleted, status` (composite filter)

#### Write Operations (30% of traffic)
- **Create Plant**: 15% - INSERT operations
- **Update Plant**: 10% - UPDATE operations
- **Delete Plant**: 2% - UPDATE (soft delete)
- **Change Status**: 5% - UPDATE operations

#### Database Load
- **Read:Write Ratio**: ~2:1 (read-heavy workload)
- **Expected Queries/sec**: 50-100 under peak load
- **Connection Pool**: Monitor for exhaustion

### Optimization Recommendations

#### 1. Database Indexes (Already Implemented)
```sql
-- Verify indexes exist
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'plant';

-- Expected indexes:
-- plant_plant_code_idx
-- plant_status_idx
-- plant_city_idx
-- plant_deleted_status_idx
```

#### 2. Query Optimization
- **Pagination**: Already implemented (reduces data transfer)
- **Select Related**: Use `select_related()` for FK fields if needed
- **Prefetch Related**: For M2M relationships

#### 3. Caching Strategy
```python
# Consider adding Redis cache for:
# - Dropdown API (frequently accessed, rarely changes)
# - Plant list with common filters
# - Plant detail views
```

#### 4. Database Connection Pooling
```python
# In settings.py, configure:
DATABASES = {
    'default': {
        # ... existing config ...
        'CONN_MAX_AGE': 600,  # Reuse connections
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

#### 5. Read Replicas (For Production)
- Use read replicas for list operations
- Route writes to primary database
- Implement in Django using database routing

## Performance Benchmarks

### Target Metrics (Load Test)
| Metric | Target | Critical |
|--------|--------|----------|
| Average Response Time | < 500ms | > 1000ms |
| 95th Percentile | < 800ms | > 2000ms |
| 99th Percentile | < 1500ms | > 5000ms |
| Error Rate | < 1% | > 5% |
| Throughput | > 50 req/s | < 20 req/s |

### Stress Test Limits
- **Maximum Users**: Identify point where response time > 5s
- **Breaking Point**: Error rate > 10%
- **Database Limits**: Connection pool exhaustion

## Monitoring During Tests

### Application Metrics
```bash
# Monitor Django server logs
tail -f logs/django.log

# Monitor database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='your_db';"

# Monitor system resources
htop  # or top
```

### Database Metrics
```sql
-- Active queries
SELECT pid, usename, query, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = 'your_db' AND state = 'active';

-- Slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE query LIKE '%plant%'
ORDER BY mean_time DESC
LIMIT 10;
```

## Troubleshooting

### High Response Times
1. Check database query performance
2. Verify indexes are being used
3. Monitor database connection pool
4. Check for N+1 query problems

### High Error Rate
1. Check authentication token expiration
2. Verify database connection limits
3. Monitor server memory/CPU
4. Check for database deadlocks

### Connection Pool Exhausted
1. Increase `CONN_MAX_AGE` in settings
2. Reduce connection pool size per process
3. Implement connection pooling (PgBouncer)
4. Use read replicas for read operations

## Best Practices

1. **Run tests in isolated environment** (not production)
2. **Warm up database** before stress tests
3. **Monitor both application and database** metrics
4. **Run tests during off-peak hours** if possible
5. **Document baseline metrics** for comparison
6. **Automate test execution** in CI/CD pipeline
7. **Set up alerts** for critical thresholds

## Continuous Performance Testing

### Integration with CI/CD
```yaml
# Example GitHub Actions workflow
- name: Run Load Tests
  run: |
    locust -f locustfile.py --host=${{ env.TEST_URL }} \
      --headless -u 50 -r 5 -t 5m \
      --csv=reports/ci_load_test \
      --html=reports/ci_load_test.html
```

### Performance Regression Detection
- Compare metrics against baseline
- Fail build if metrics exceed thresholds
- Generate performance reports

## Additional Resources

- [Locust Documentation](https://docs.locust.io/)
- [Django Performance Best Practices](https://docs.djangoproject.com/en/stable/topics/performance/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)

