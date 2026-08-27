"""
Item Category Master API Tests
Comprehensive test coverage for all Item Category endpoints
"""

import io
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from common.models import ItemCategory
from imports.services.item_category_importer import ItemCategoryImporter

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user"""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Create authenticated API client"""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def item_category_data():
    """Item Category creation data"""
    return {
        "category_code": "CAT-RAW-001",
        "category_name": "Raw Material - Aluminum Ingots",
        "allowed_item_type": "RAW",
        "description": "Aluminum ingots and billets for extrusion",
        "is_active": True,
    }


@pytest.fixture
def item_category(db, user, item_category_data):
    """Create test item category"""
    return ItemCategory.objects.create(
        category_code=item_category_data["category_code"],
        category_name=item_category_data["category_name"],
        allowed_item_type=item_category_data["allowed_item_type"],
        description=item_category_data["description"],
        is_active=item_category_data["is_active"],
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def archived_item_category(db, user):
    """Create archived item category"""
    return ItemCategory.objects.create(
        category_code="CAT-ARCH-001",
        category_name="Archived Category",
        allowed_item_type="RAW",
        is_active=False,
        is_archived=True,
        created_by=user,
        updated_by=user,
    )


class TestItemCategoryModel:
    """Test ItemCategory model"""

    def test_item_category_str(self, item_category):
        """Test ItemCategory string representation"""
        assert (
            str(item_category)
            == f"{item_category.category_code} - {item_category.category_name}"
        )

    def test_item_category_code_normalization(self, db, user):
        """Test category_code is normalized to uppercase"""
        category = ItemCategory.objects.create(
            category_code="cat-test-001",
            category_name="Test Category",
            allowed_item_type="RAW",
            created_by=user,
            updated_by=user,
        )
        assert category.category_code == "CAT-TEST-001"

    def test_item_category_hard_delete_prevented(self, item_category):
        """Test hard delete is prevented"""
        with pytest.raises(ValueError, match="Hard delete not allowed"):
            item_category.delete()


class TestItemCategoryCreate:
    """Test Item Category creation"""

    def test_create_item_category(self, authenticated_client, item_category_data, user):
        """Test creating item category"""
        url = reverse("item-category-list")
        response = authenticated_client.post(url, item_category_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["category_code"] == "CAT-RAW-001"
        assert ItemCategory.objects.filter(category_code="CAT-RAW-001").exists()

    def test_create_item_category_duplicate_code(
        self, authenticated_client, item_category, item_category_data
    ):
        """Test creating item category with duplicate code fails"""
        url = reverse("item-category-list")
        response = authenticated_client.post(url, item_category_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_item_category_case_insensitive_duplicate(
        self, authenticated_client, item_category
    ):
        """Test case-insensitive duplicate detection"""
        url = reverse("item-category-list")
        data = {
            "category_code": "cat-raw-001",  # lowercase
            "category_name": "Another Category",
            "allowed_item_type": "RAW",
        }
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_item_category_missing_required_fields(self, authenticated_client):
        """Test creating item category without required fields fails"""
        url = reverse("item-category-list")
        response = authenticated_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_item_category_invalid_item_type(self, authenticated_client):
        """Test creating item category with invalid item type fails"""
        url = reverse("item-category-list")
        data = {
            "category_code": "CAT-TEST-001",
            "category_name": "Test Category",
            "allowed_item_type": "INVALID_TYPE",
        }
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_item_category_all_item_types(self, authenticated_client, user):
        """Test creating categories with all valid item types"""
        url = reverse("item-category-list")
        item_types = ["RAW", "CONSUMABLE", "SEMI", "FG", "SPARE", "SCRAP", "TOOLING"]

        for idx, item_type in enumerate(item_types):
            data = {
                "category_code": f"CAT-{item_type}-{idx:03d}",
                "category_name": f"Category {item_type}",
                "allowed_item_type": item_type,
            }
            response = authenticated_client.post(url, data, format="json")
            assert response.status_code == status.HTTP_201_CREATED


class TestItemCategoryList:
    """Test Item Category listing"""

    def test_list_item_categories(self, authenticated_client, item_category):
        """Test listing item categories"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]["results"]) > 0

    def test_list_item_categories_with_filters(
        self, authenticated_client, item_category
    ):
        """Test listing item categories with filters"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url, {"is_active": "true"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_item_categories_with_item_type_filter(
        self, authenticated_client, item_category
    ):
        """Test filtering by allowed_item_type"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url, {"allowed_item_type": "RAW"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_item_categories_with_search(
        self, authenticated_client, item_category
    ):
        """Test listing item categories with search"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url, {"search": "CAT-RAW-001"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_item_categories_with_ordering(
        self, authenticated_client, item_category
    ):
        """Test listing item categories with ordering"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url, {"ordering": "-category_code"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_item_categories_excludes_archived(
        self, authenticated_client, item_category, archived_item_category
    ):
        """Test archived categories are excluded from list"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        category_ids = [cat["id"] for cat in response.data["data"]["results"]]
        assert str(archived_item_category.id) not in category_ids


class TestItemCategoryRetrieve:
    """Test Item Category retrieval"""

    def test_retrieve_item_category(self, authenticated_client, item_category):
        """Test retrieving a single item category"""
        url = reverse("item-category-detail", kwargs={"pk": item_category.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["category_code"] == "CAT-RAW-001"

    def test_retrieve_nonexistent_item_category(self, authenticated_client):
        """Test retrieving non-existent item category returns 404"""
        import uuid

        url = reverse("item-category-detail", kwargs={"pk": uuid.uuid4()})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestItemCategoryUpdate:
    """Test Item Category updates"""

    def test_update_item_category(self, authenticated_client, item_category):
        """Test updating item category"""
        url = reverse("item-category-detail", kwargs={"pk": item_category.id})
        data = {
            "category_code": "CAT-RAW-001",
            "category_name": "Updated Category Name",
            "allowed_item_type": "RAW",
            "description": "Updated description",
            "is_active": True,
        }
        response = authenticated_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["category_name"] == "Updated Category Name"

    def test_partial_update_item_category(self, authenticated_client, item_category):
        """Test partial update of item category"""
        url = reverse("item-category-detail", kwargs={"pk": item_category.id})
        data = {"category_name": "Partially Updated Name"}
        response = authenticated_client.patch(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["category_name"] == "Partially Updated Name"

    def test_update_archived_item_category_fails(
        self, authenticated_client, archived_item_category
    ):
        """Test updating archived item category fails"""
        url = reverse("item-category-detail", kwargs={"pk": archived_item_category.id})
        data = {"category_name": "Updated Name"}
        response = authenticated_client.patch(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestItemCategoryStatusChange:
    """Test Item Category status changes"""

    def test_change_status_to_inactive(self, authenticated_client, item_category):
        """Test changing status to inactive"""
        url = reverse("item-category-change-status", kwargs={"pk": item_category.id})
        response = authenticated_client.post(url, {"status": "Inactive"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        item_category.refresh_from_db()
        assert item_category.is_active is False

    def test_change_status_to_active(self, authenticated_client, db, user):
        """Test changing status to active"""
        category = ItemCategory.objects.create(
            category_code="CAT-INACTIVE",
            category_name="Inactive Category",
            allowed_item_type="RAW",
            is_active=False,
            created_by=user,
            updated_by=user,
        )
        url = reverse("item-category-change-status", kwargs={"pk": category.id})
        response = authenticated_client.post(url, {"status": "Active"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        category.refresh_from_db()
        assert category.is_active is True

    def test_change_status_missing_field(self, authenticated_client, item_category):
        """Test status change without status field fails"""
        url = reverse("item-category-change-status", kwargs={"pk": item_category.id})
        response = authenticated_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_status_invalid_value(self, authenticated_client, item_category):
        """Test status change with invalid status fails"""
        url = reverse("item-category-change-status", kwargs={"pk": item_category.id})
        response = authenticated_client.post(url, {"status": "Invalid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestItemCategoryDelete:
    """Test Item Category deletion (archive)"""

    def test_delete_item_category(self, authenticated_client, db, user):
        """Test soft delete (archive) item category"""
        category = ItemCategory.objects.create(
            category_code="CAT-DELETE",
            category_name="Category to Delete",
            allowed_item_type="RAW",
            is_active=False,  # Must be inactive to archive
            created_by=user,
            updated_by=user,
        )
        url = reverse("item-category-detail", kwargs={"pk": category.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        category.refresh_from_db()
        assert category.is_archived is True

    def test_delete_active_item_category_fails(
        self, authenticated_client, item_category
    ):
        """Test cannot archive active item category"""
        url = reverse("item-category-detail", kwargs={"pk": item_category.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active" in response.data["message"].lower()

    def test_delete_already_archived_category_fails(
        self, authenticated_client, archived_item_category
    ):
        """Test cannot archive already archived category"""
        url = reverse("item-category-detail", kwargs={"pk": archived_item_category.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestItemCategoryDropdown:
    """Test Item Category dropdown API"""

    def test_dropdown_api(self, authenticated_client, item_category):
        """Test dropdown API returns active categories only"""
        url = reverse("item-category-dropdown")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]) > 0
        # Check structure
        category = response.data["data"][0]
        assert "id" in category
        assert "category_code" in category
        assert "category_name" in category
        assert "allowed_item_type" in category

    def test_dropdown_api_excludes_inactive(self, authenticated_client, db, user):
        """Test dropdown excludes inactive categories"""
        active_category = ItemCategory.objects.create(
            category_code="CAT-ACTIVE",
            category_name="Active Category",
            allowed_item_type="RAW",
            is_active=True,
            created_by=user,
            updated_by=user,
        )
        inactive_category = ItemCategory.objects.create(
            category_code="CAT-INACTIVE",
            category_name="Inactive Category",
            allowed_item_type="RAW",
            is_active=False,
            created_by=user,
            updated_by=user,
        )
        url = reverse("item-category-dropdown")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        category_ids = [cat["id"] for cat in response.data["data"]]
        assert str(active_category.id) in category_ids
        assert str(inactive_category.id) not in category_ids

    def test_dropdown_api_excludes_archived(
        self, authenticated_client, item_category, archived_item_category
    ):
        """Test dropdown excludes archived categories"""
        url = reverse("item-category-dropdown")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        category_ids = [cat["id"] for cat in response.data["data"]]
        assert str(item_category.id) in category_ids
        assert str(archived_item_category.id) not in category_ids

    def test_dropdown_api_with_item_type_filter(self, authenticated_client, db, user):
        """Test dropdown with item_type filter"""
        raw_category = ItemCategory.objects.create(
            category_code="CAT-RAW",
            category_name="Raw Category",
            allowed_item_type="RAW",
            is_active=True,
            created_by=user,
            updated_by=user,
        )
        fg_category = ItemCategory.objects.create(
            category_code="CAT-FG",
            category_name="Finished Goods Category",
            allowed_item_type="FG",
            is_active=True,
            created_by=user,
            updated_by=user,
        )
        url = reverse("item-category-dropdown")
        response = authenticated_client.get(url, {"item_type": "RAW"})
        assert response.status_code == status.HTTP_200_OK
        category_ids = [cat["id"] for cat in response.data["data"]]
        assert str(raw_category.id) in category_ids
        assert str(fg_category.id) not in category_ids


class TestItemCategoryBulkArchive:
    """Test Item Category bulk archive"""

    def test_bulk_archive_categories(self, authenticated_client, db, user):
        """Test bulk archive item categories"""
        category1 = ItemCategory.objects.create(
            category_code="CAT-BULK-001",
            category_name="Bulk Category 1",
            allowed_item_type="RAW",
            is_active=False,
            created_by=user,
            updated_by=user,
        )
        category2 = ItemCategory.objects.create(
            category_code="CAT-BULK-002",
            category_name="Bulk Category 2",
            allowed_item_type="CONSUMABLE",
            is_active=False,
            created_by=user,
            updated_by=user,
        )
        url = reverse("item-category-bulk-archive")
        response = authenticated_client.post(
            url, {"ids": [str(category1.id), str(category2.id)]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        category1.refresh_from_db()
        category2.refresh_from_db()
        assert category1.is_archived is True
        assert category2.is_archived is True

    def test_bulk_archive_missing_ids(self, authenticated_client):
        """Test bulk archive without ids fails"""
        url = reverse("item-category-bulk-archive")
        response = authenticated_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_archive_active_category_fails(
        self, authenticated_client, item_category
    ):
        """Test bulk archive fails for active categories"""
        url = reverse("item-category-bulk-archive")
        response = authenticated_client.post(
            url, {"ids": [str(item_category.id)]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        # Should have errors in response
        assert "errors" in response.data["data"]


class TestItemCategoryBulkRestore:
    """Test Item Category bulk restore"""

    def test_bulk_restore_categories(
        self, authenticated_client, archived_item_category, db, user
    ):
        """Test bulk restore archived item categories"""
        archived_category2 = ItemCategory.objects.create(
            category_code="CAT-ARCH-002",
            category_name="Archived Category 2",
            allowed_item_type="RAW",
            is_active=False,
            is_archived=True,
            created_by=user,
            updated_by=user,
        )
        url = reverse("item-category-bulk-restore")
        response = authenticated_client.post(
            url,
            {"ids": [str(archived_item_category.id), str(archived_category2.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        archived_item_category.refresh_from_db()
        archived_category2.refresh_from_db()
        assert archived_item_category.is_archived is False
        assert archived_category2.is_archived is False


class TestItemCategoryArchived:
    """Test archived item categories endpoints"""

    def test_list_archived_categories(
        self, authenticated_client, item_category, archived_item_category
    ):
        """Test listing archived categories"""
        url = reverse("item-category-list-archived")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        category_ids = [cat["id"] for cat in response.data["data"]["results"]]
        assert str(archived_item_category.id) in category_ids
        assert str(item_category.id) not in category_ids

    def test_get_archived_category_details(
        self, authenticated_client, archived_item_category
    ):
        """Test getting archived category details"""
        url = reverse(
            "item-category-get-archived", kwargs={"pk": archived_item_category.id}
        )
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["category_code"] == "CAT-ARCH-001"

    def test_get_nonexistent_archived_category(self, authenticated_client):
        """Test getting non-existent archived category returns 404"""
        import uuid

        url = reverse("item-category-get-archived", kwargs={"pk": uuid.uuid4()})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestItemCategoryPermissions:
    """Test Item Category permissions"""

    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated requests are denied"""
        url = reverse("item-category-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_access_allowed(self, authenticated_client, item_category):
        """Test authenticated requests are allowed"""
        url = reverse("item-category-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK


class TestItemCategoryBulkImportRowErrors:
    """Test Item Category bulk import returns row_errors (no skipped_details in response)."""

    def test_validation_row_errors_returned(self, db, user):
        """Import with invalid rows: row_errors is populated, skipped_details not in response."""
        csv_content = (
            "Category Code,Category Name,Allowed Item Type,Description,Is Active\n"
            "CAT-T1,Valid Category,RAW,Desc,True\n"
            "CAT-T2,Invalid Row,,Desc,True\n"
        )
        buf = io.BytesIO(csv_content.encode("utf-8"))
        buf.name = "test_item_category.csv"
        importer = ItemCategoryImporter(buf, user=user, dry_run=False)
        result = importer.import_data()
        assert "row_errors" in result
        assert "skipped_details" not in result
        row_errors = result["row_errors"]
        assert isinstance(row_errors, list)
        assert len(row_errors) >= 1
        first_error = row_errors[0]
        assert "row_number" in first_error
        assert "errors" in first_error
        assert "row_data" in first_error
        assert isinstance(first_error["errors"], list)
        assert len(first_error["errors"]) >= 1
        assert first_error["errors"][0].get("field") or first_error["errors"][0].get(
            "message"
        )

    def test_validation_row_errors_structure(self, db, user):
        """Each row error has row_number, errors (field, message, value), row_data."""
        csv_content = (
            "Category Code,Category Name,Allowed Item Type\n"
            "CAT-ERR1,Bad Code!,INVALID_TYPE\n"
        )
        buf = io.BytesIO(csv_content.encode("utf-8"))
        buf.name = "test.csv"
        importer = ItemCategoryImporter(buf, user=user, dry_run=False)
        result = importer.import_data()
        assert "row_errors" in result
        assert "skipped_details" not in result
        assert len(result["row_errors"]) >= 1
        err = result["row_errors"][0]
        assert err["row_number"] >= 1
        assert all(
            e.get("field") is not None or e.get("message") for e in err["errors"]
        )
        assert "row_data" in err
