"""
Database Stress Testing for Item Category Module
Tests performance with 10,000+ categories
"""

import os
import time

import django
from django.db import connection, reset_queries

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alux_erp.settings")
django.setup()

import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone

from common.models import ItemCategory

User = get_user_model()


def create_test_categories(count=10000):
    """Create large number of test categories for stress testing"""
    print(f"\n{'='*60}")
    print(f"Creating {count} test categories for stress testing...")
    print(f"{'='*60}\n")

    # Get or create test user
    user, _ = User.objects.get_or_create(
        username="stress_test_user",
        defaults={"email": "stresstest@example.com", "is_active": True},
    )

    item_types = ["RAW", "CONSUMABLE", "SEMI", "FG", "SPARE", "SCRAP", "TOOLING"]
    categories = []
    batch_size = 500

    start_time = time.time()

    for i in range(count):
        category = ItemCategory(
            id=uuid.uuid4(),
            category_code=f"STRESS-{item_types[i % len(item_types)]}-{i+1:05d}",
            category_name=f"Stress Test Category {i+1}",
            allowed_item_type=item_types[i % len(item_types)],
            description=f"Stress test category #{i+1}",
            is_active=True,
            is_archived=False,
            created_by=user,
            updated_by=user,
        )
        categories.append(category)

        # Bulk create in batches
        if len(categories) >= batch_size:
            ItemCategory.objects.bulk_create(categories, ignore_conflicts=True)
            print(f"Created batch: {len(categories)} categories (Total: {i+1}/{count})")
            categories = []

    # Create remaining
    if categories:
        ItemCategory.objects.bulk_create(categories, ignore_conflicts=True)
        print(f"Created final batch: {len(categories)} categories")

    elapsed = time.time() - start_time
    print(f"\n✅ Created {count} categories in {elapsed:.2f} seconds")
    print(f"   Average: {elapsed/count*1000:.2f}ms per category\n")

    return count


def test_list_performance():
    """Test list API performance with large dataset"""
    print(f"\n{'='*60}")
    print("Testing List API Performance")
    print(f"{'='*60}\n")

    reset_queries()
    start_time = time.time()

    # Test 1: Simple list
    queryset = ItemCategory.objects.filter(is_archived=False).select_related(
        "created_by", "updated_by"
    )[:100]
    list(queryset)

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"✅ Simple list (100 records):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")
    print(f"   Avg per query: {elapsed/query_count*1000:.2f}ms")

    # Test 2: List with filters
    reset_queries()
    start_time = time.time()

    queryset = ItemCategory.objects.filter(
        is_archived=False, is_active=True, allowed_item_type="RAW"
    ).select_related("created_by", "updated_by")[:100]
    list(queryset)

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"\n✅ Filtered list (is_active=True, allowed_item_type=RAW, 100 records):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")

    # Test 3: List with search
    reset_queries()
    start_time = time.time()

    queryset = ItemCategory.objects.filter(
        is_archived=False, category_code__icontains="STRESS"
    ).select_related("created_by", "updated_by")[:100]
    list(queryset)

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"\n✅ Search list (category_code contains 'STRESS', 100 records):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")


def test_dropdown_performance():
    """Test dropdown API performance"""
    print(f"\n{'='*60}")
    print("Testing Dropdown API Performance")
    print(f"{'='*60}\n")

    reset_queries()
    start_time = time.time()

    queryset = ItemCategory.objects.filter(is_active=True, is_archived=False)
    count = queryset.count()
    list(
        queryset.values("id", "category_code", "category_name", "allowed_item_type")[
            :100
        ]
    )

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"✅ Dropdown query (total: {count} records, fetched: 100):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")

    # Test with filter
    reset_queries()
    start_time = time.time()

    queryset = ItemCategory.objects.filter(
        is_active=True, is_archived=False, allowed_item_type="RAW"
    )
    count = queryset.count()
    list(
        queryset.values("id", "category_code", "category_name", "allowed_item_type")[
            :100
        ]
    )

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"\n✅ Dropdown with filter (item_type=RAW, total: {count}, fetched: 100):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")


def test_pagination_performance():
    """Test pagination performance with large dataset"""
    print(f"\n{'='*60}")
    print("Testing Pagination Performance")
    print(f"{'='*60}\n")

    page_sizes = [10, 50, 100, 500]

    for page_size in page_sizes:
        reset_queries()
        start_time = time.time()

        queryset = ItemCategory.objects.filter(is_archived=False).select_related(
            "created_by", "updated_by"
        )[:page_size]
        list(queryset)

        elapsed = time.time() - start_time
        query_count = len(connection.queries)

        print(f"✅ Page size {page_size}:")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   Queries: {query_count}")
        print(f"   Time per record: {elapsed/page_size*1000:.2f}ms")


def test_bulk_operations_performance():
    """Test bulk archive/restore performance"""
    print(f"\n{'='*60}")
    print("Testing Bulk Operations Performance")
    print(f"{'='*60}\n")

    # Get test categories
    test_categories = list(
        ItemCategory.objects.filter(
            category_code__startswith="STRESS-", is_archived=False
        )[:1000]
    )

    if not test_categories:
        print("⚠️  No test categories found. Run create_test_categories() first.")
        return

    # Test bulk archive
    reset_queries()
    start_time = time.time()

    category_ids = [str(cat.id) for cat in test_categories[:100]]
    ItemCategory.objects.filter(id__in=category_ids).update(
        is_archived=True, updated_at=timezone.now()
    )

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"✅ Bulk archive (100 categories):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")

    # Test bulk restore
    reset_queries()
    start_time = time.time()

    ItemCategory.objects.filter(id__in=category_ids).update(
        is_archived=False, updated_at=timezone.now()
    )

    elapsed = time.time() - start_time
    query_count = len(connection.queries)

    print(f"\n✅ Bulk restore (100 categories):")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Queries: {query_count}")


def cleanup_test_data():
    """Clean up stress test data"""
    print(f"\n{'='*60}")
    print("Cleaning up stress test data...")
    print(f"{'='*60}\n")

    deleted_count = ItemCategory.objects.filter(
        category_code__startswith="STRESS-"
    ).delete()[0]

    print(f"✅ Deleted {deleted_count} test categories")


def run_stress_tests():
    """Run all stress tests"""
    print("\n" + "=" * 60)
    print("ITEM CATEGORY MODULE - DATABASE STRESS TESTING")
    print("=" * 60)

    # Check current count
    current_count = ItemCategory.objects.count()
    print(f"\nCurrent ItemCategory count: {current_count}")

    # Ask user
    response = input("\nCreate 10,000 test categories? (y/n): ")
    if response.lower() == "y":
        create_test_categories(10000)

    # Run performance tests
    test_list_performance()
    test_dropdown_performance()
    test_pagination_performance()
    test_bulk_operations_performance()

    # Cleanup option
    response = input("\nClean up test data? (y/n): ")
    if response.lower() == "y":
        cleanup_test_data()

    print("\n" + "=" * 60)
    print("STRESS TESTING COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_stress_tests()
