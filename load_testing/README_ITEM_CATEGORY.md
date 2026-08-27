# Item Category Master - Load Testing Guide

## Overview

This document provides comprehensive load testing guidelines for the Item Category Master APIs using Locust.

## Prerequisites

1. **Install Locust:**
   ```bash
   pip install locust
   ```

2. **Create Test Users:**
   Create the following test users in your database:
   - loadtest1@example.com
   - loadtest2@example.com
   - loadtest3@example.com
   - loadtest4@example.com
   - loadtest5@example.com
   
   All with password: `TestPass123!`

3. **Ensure Test Data:**
   - Have at least 10-20 item categories in the database
   - Ensure test users have proper permissions

## Test Scenarios

### 1. Smoke Test (Quick Validation)
**Purpose:** Verify all endpoints are working
```bash
locust -f locustfile_item_category.py --host=http://localhost:8000 --headless -u 5 -r 1 -t 2m
```

### 2. Load Test (Normal Load)
**Purpose:** Test system under expected production load
```bash
locust -f locustfile_item_category.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 10m --csv=reports/item_category_load
```

### 3. Stress Test (Peak Load)
**Purpose:** Test system limits
```bash
locust -f locustfile_item_category.py --host=http://localhost:8000 --headless -u 500 -r 50 -t 15m --csv=reports/item_category_stress
```

### 4. Soak Test (Endurance)
**Purpose:** Test system stability over extended period
```bash
locust -f locustfile_item_category.py --host=http://localhost:8000 --headless -u 200 -r 20 -t 1h --csv=reports/item_category_soak
```

## Interactive Mode

For interactive testing with web UI:
```bash
locust -f locustfile_item_category.py --host=http://localhost:8000
```

Then open: http://localhost:8089

## Test Metrics

### Key Performance Indicators (KPIs)

1. **Response Time Targets:**
   - List API: < 500ms (p95)
   - Dropdown API: < 300ms (p95)
   - Create/Update: < 500ms (p95)
   - Retrieve: < 300ms (p95)

2. **Throughput:**
   - Minimum: 100 requests/second
   - Target: 200+ requests/second

3. **Error Rate:**
   - Target: < 1% error rate
   - Critical: < 0.1% for 5xx errors

4. **Database Performance:**
   - Query execution time: < 100ms (p95)
   - Connection pool utilization: < 80%

## Monitoring During Tests

### Database Metrics
- Monitor query execution times
- Check for N+1 query issues
- Monitor connection pool usage
- Track slow queries

### Application Metrics
- CPU usage
- Memory consumption
- Request queue length
- Response time percentiles

### API Metrics
- Success rate
- Error rate by type
- Response time distribution
- Throughput (requests/second)

## Expected Results

### Load Test (100 users)
- **Response Times:**
  - List: ~200-300ms (p95)
  - Dropdown: ~100-150ms (p95)
  - Create: ~300-400ms (p95)
  - Update: ~250-350ms (p95)

- **Throughput:** 150-200 req/s
- **Error Rate:** < 0.5%

### Stress Test (500 users)
- **Response Times:**
  - May increase to 500-800ms (p95)
  - System should remain stable
  - No memory leaks

- **Throughput:** 300-400 req/s
- **Error Rate:** < 2%

## Troubleshooting

### High Response Times
1. Check database query performance
2. Verify indexes are being used
3. Check for N+1 query issues
4. Monitor connection pool

### High Error Rates
1. Check authentication token expiration
2. Verify database connection limits
3. Check application logs for errors
4. Monitor server resources

### Memory Issues
1. Check for memory leaks in code
2. Monitor database connection pool
3. Verify query result caching
4. Check for unbounded result sets

## Optimization Recommendations

1. **Database:**
   - Ensure proper indexes on category_code, allowed_item_type, is_active, is_archived
   - Use select_related for foreign keys
   - Implement query result caching

2. **API:**
   - Implement response caching for dropdown API
   - Use pagination efficiently
   - Optimize serializer queries

3. **Infrastructure:**
   - Use connection pooling
   - Implement rate limiting
   - Use CDN for static assets

## Report Analysis

After running tests, analyze:
1. Response time percentiles (p50, p95, p99)
2. Error rate and error types
3. Throughput trends
4. Resource utilization
5. Database query performance

## Best Practices

1. Run tests in isolated environment
2. Use realistic test data
3. Monitor all system components
4. Document all findings
5. Compare results across test runs
6. Set up alerts for critical metrics

