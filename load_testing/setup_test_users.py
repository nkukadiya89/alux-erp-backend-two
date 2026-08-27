"""
Script to create test users for load testing
Run: python load_testing/setup_test_users.py
"""

import os
import sys

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alux_erp.settings")
django.setup()

from user.models import User

TEST_USERS = [
    {"email": "loadtest1@example.com", "password": "TestPass123!"},
    {"email": "loadtest2@example.com", "password": "TestPass123!"},
    {"email": "loadtest3@example.com", "password": "TestPass123!"},
    {"email": "loadtest4@example.com", "password": "TestPass123!"},
    {"email": "loadtest5@example.com", "password": "TestPass123!"},
]


def create_test_users():
    """Create test users for load testing"""
    created = 0
    updated = 0

    for user_data in TEST_USERS:
        user, created_flag = User.objects.get_or_create(
            email=user_data["email"],
            defaults={
                "first_name": "Load",
                "last_name": "Test",
                "is_active": True,
                "is_staff": False,
            },
        )

        # Always update password
        user.set_password(user_data["password"])
        user.is_active = True
        user.save()

        if created_flag:
            created += 1
            print(f"✓ Created user: {user.email}")
        else:
            updated += 1
            print(f"✓ Updated user: {user.email}")

    print(f"\nSummary: {created} created, {updated} updated")


if __name__ == "__main__":
    create_test_users()
