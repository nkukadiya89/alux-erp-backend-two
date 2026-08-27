# Quick Start Guide - Plant Master Load Testing

## 1. Installation

```bash
pip install -r load_testing/requirements.txt
```

## 2. Setup Test Users

```bash
python load_testing/setup_test_users.py
```

## 3. Run Tests

### Interactive Mode (Recommended for first run)
```bash
locust -f locustfile.py --host=http://localhost:8000
```
Open browser: http://localhost:8089

### Automated Tests

#### Smoke Test (2 minutes)
```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 5 -r 1 -t 2m
```

#### Load Test (10 minutes)
```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 10m \
    --csv=reports/load_test --html=reports/load_test.html
```

#### Stress Test (20 minutes)
```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 300 -r 10 -t 20m \
    --csv=reports/stress_test --html=reports/stress_test.html
```

## 4. View Results

- **CSV Reports**: `reports/*_test_stats.csv`
- **HTML Report**: Open `reports/*_test.html` in browser
- **Console Output**: Real-time metrics during test

## 5. Key Metrics to Monitor

- **Response Time**: Average < 500ms, 95th percentile < 800ms
- **Error Rate**: Should be < 1%
- **Throughput**: Requests per second
- **Failures**: Check `*_failures.csv` for details

## Troubleshooting

### Authentication Errors
- Ensure test users are created: `python load_testing/setup_test_users.py`
- Check user credentials in `locustfile.py` match database

### Connection Errors
- Verify Django server is running: `python manage.py runserver`
- Check BASE_URL in locustfile.py matches your server

### High Response Times
- Check database performance
- Monitor server resources (CPU, memory)
- Review database indexes

## Next Steps

- Read full documentation: `load_testing/README.md`
- Review optimization recommendations: `load_testing/OPTIMIZATION_RECOMMENDATIONS.md`
- Analyze reports and identify bottlenecks

