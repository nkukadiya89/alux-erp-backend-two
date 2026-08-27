#!/bin/bash

# Plant Master Load Testing Script
# Usage: ./run_tests.sh [test_type]
# test_type: smoke, load, stress, soak

TEST_TYPE=${1:-load}
BASE_URL=${BASE_URL:-http://localhost:8000}
REPORTS_DIR="reports"
mkdir -p $REPORTS_DIR

case $TEST_TYPE in
    smoke)
        echo "Running Smoke Test..."
        locust -f locustfile.py \
            --host=$BASE_URL \
            --headless \
            -u 5 \
            -r 1 \
            -t 2m \
            --csv=$REPORTS_DIR/smoke_test \
            --html=$REPORTS_DIR/smoke_test.html
        ;;
    load)
        echo "Running Load Test..."
        locust -f locustfile.py \
            --host=$BASE_URL \
            --headless \
            -u 100 \
            -r 10 \
            -t 10m \
            --csv=$REPORTS_DIR/load_test \
            --html=$REPORTS_DIR/load_test.html
        ;;
    stress)
        echo "Running Stress Test..."
        locust -f locustfile.py \
            --host=$BASE_URL \
            --headless \
            -u 300 \
            -r 10 \
            -t 20m \
            --csv=$REPORTS_DIR/stress_test \
            --html=$REPORTS_DIR/stress_test.html
        ;;
    soak)
        echo "Running Soak Test..."
        locust -f locustfile.py \
            --host=$BASE_URL \
            --headless \
            -u 150 \
            -r 5 \
            -t 30m \
            --csv=$REPORTS_DIR/soak_test \
            --html=$REPORTS_DIR/soak_test.html
        ;;
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Usage: ./run_tests.sh [smoke|load|stress|soak]"
        exit 1
        ;;
esac

echo "Test completed. Reports saved in $REPORTS_DIR/"

