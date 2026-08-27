"""
Department Master API Tests
Comprehensive test coverage for all Department endpoints
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from common.models import Department, Plant, PlantType

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
def plant_type(db, user):
    """Create test plant type"""
    return PlantType.objects.create(
        code="PT001",
        name="Test Plant Type",
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def plant(db, user, plant_type):
    """Create test plant"""
    return Plant.objects.create(
        plant_code="PLT001",
        plant_name="Test Plant",
        plant_type=plant_type,
        status="Active",
        address_line_1="123 Test Street",
        city="Test City",
        state="Test State",
        country="Test Country",
        postal_code="12345",
        phone_number="1234567890",
        email="plant@test.com",
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def department_data(plant):
    """Department creation data"""
    return {
        "department_code": "DEPT-001",
        "department_name": "Production Department",
        "department_type": "PRODUCTION",
        "plant": str(plant.id),
        "cost_center_code": "CC-001",
        "status": "Active",
    }


@pytest.fixture
def department_data_no_plant():
    """Department creation data without plant"""
    return {
        "department_code": "DEPT-002",
        "department_name": "Head Office Department",
        "department_type": "ADMIN",
        "status": "Active",
    }


@pytest.fixture
def department(db, user, plant, department_data):
    """Create test department"""
    return Department.objects.create(
        department_code=department_data["department_code"],
        department_name=department_data["department_name"],
        department_type=department_data["department_type"],
        plant=plant,
        cost_center_code=department_data["cost_center_code"],
        status=department_data["status"],
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def parent_department(db, user, plant):
    """Create parent department"""
    return Department.objects.create(
        department_code="DEPT-PARENT",
        department_name="Parent Department",
        department_type="ADMIN",
        plant=plant,
        status="Active",
        created_by=user,
        updated_by=user,
    )


@pytest.mark.django_db
class TestDepartmentModel:
    """Test Department Model"""

    def test_department_creation(self, user, plant, department_data):
        """Test creating a department"""
        department = Department.objects.create(
            **department_data, plant=plant, created_by=user, updated_by=user
        )
        assert department.department_code == "DEPT-001"
        assert department.department_name == "Production Department"
        assert department.status == "Active"
        assert str(department) == "DEPT-001 - Production Department"

    def test_department_creation_without_plant(self, user, department_data_no_plant):
        """Test creating a department without plant"""
        department = Department.objects.create(
            **department_data_no_plant, created_by=user, updated_by=user
        )
        assert department.department_code == "DEPT-002"
        assert department.plant is None

    def test_department_code_unique(self, user, plant, department_data):
        """Test department_code uniqueness"""
        Department.objects.create(
            **department_data, plant=plant, created_by=user, updated_by=user
        )
        with pytest.raises(Exception):
            Department.objects.create(
                **department_data, plant=plant, created_by=user, updated_by=user
            )

    def test_department_code_case_insensitive(self, user, plant, department_data):
        """Test department_code is case-insensitive unique"""
        Department.objects.create(
            **department_data, plant=plant, created_by=user, updated_by=user
        )
        department_data["department_code"] = "dept-001"  # lowercase
        with pytest.raises(Exception):
            Department.objects.create(
                **department_data, plant=plant, created_by=user, updated_by=user
            )

    def test_department_code_normalized(self, user, plant):
        """Test department_code is normalized to uppercase"""
        department = Department.objects.create(
            department_code="dept-003",
            department_name="Test Dept",
            department_type="PRODUCTION",
            plant=plant,
            status="Active",
            created_by=user,
            updated_by=user,
        )
        assert department.department_code == "DEPT-003"

    def test_hard_delete_prevented(self, department):
        """Test hard delete is prevented"""
        with pytest.raises(ValueError, match="Hard delete not allowed"):
            department.delete()


@pytest.mark.django_db
class TestDepartmentAPI:
    """Test Department API endpoints"""

    def test_create_department_success(
        self, authenticated_client, plant, department_data
    ):
        """Test successful department creation"""
        url = reverse("department-list")
        response = authenticated_client.post(url, department_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["department_code"] == "DEPT-001"
        assert Department.objects.filter(department_code="DEPT-001").exists()

    def test_create_department_without_plant(
        self, authenticated_client, department_data_no_plant
    ):
        """Test creating department without plant"""
        url = reverse("department-list")
        response = authenticated_client.post(
            url, department_data_no_plant, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["plant"] is None

    def test_create_department_duplicate_code(
        self, authenticated_client, department, department_data, plant
    ):
        """Test creating department with duplicate code fails"""
        url = reverse("department-list")
        response = authenticated_client.post(url, department_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_department_case_insensitive_duplicate(
        self, authenticated_client, department, plant
    ):
        """Test case-insensitive duplicate detection"""
        url = reverse("department-list")
        data = {
            "department_code": "dept-001",  # lowercase
            "department_name": "Another Dept",
            "department_type": "PRODUCTION",
            "plant": str(plant.id),
            "status": "Active",
        }
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_department_missing_required_fields(self, authenticated_client):
        """Test creating department without required fields fails"""
        url = reverse("department-list")
        response = authenticated_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_department_with_parent(
        self, authenticated_client, plant, parent_department
    ):
        """Test creating department with parent department"""
        url = reverse("department-list")
        data = {
            "department_code": "DEPT-CHILD",
            "department_name": "Child Department",
            "department_type": "PRODUCTION",
            "plant": str(plant.id),
            "parent_department": str(parent_department.id),
            "status": "Active",
        }
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["parent_department"] == str(parent_department.id)

    def test_list_departments(self, authenticated_client, department):
        """Test listing departments"""
        url = reverse("department-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]["results"]) > 0

    def test_list_departments_with_filters(self, authenticated_client, department):
        """Test listing departments with filters"""
        url = reverse("department-list")
        response = authenticated_client.get(url, {"status": "Active"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_departments_with_department_type_filter(
        self, authenticated_client, department
    ):
        """Test filtering by department_type"""
        url = reverse("department-list")
        response = authenticated_client.get(url, {"department_type": "PRODUCTION"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_departments_with_plant_filter(
        self, authenticated_client, department, plant
    ):
        """Test filtering by plant"""
        url = reverse("department-list")
        response = authenticated_client.get(url, {"plant": str(plant.id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_departments_with_search(self, authenticated_client, department):
        """Test listing departments with search"""
        url = reverse("department-list")
        response = authenticated_client.get(url, {"search": "DEPT-001"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_departments_with_ordering(self, authenticated_client, department):
        """Test listing departments with ordering"""
        url = reverse("department-list")
        response = authenticated_client.get(url, {"ordering": "-department_code"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_retrieve_department(self, authenticated_client, department):
        """Test retrieving a single department"""
        url = reverse("department-detail", kwargs={"pk": department.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["id"] == str(department.id)

    def test_update_department_put(self, authenticated_client, department):
        """Test full update of department (PUT)"""
        url = reverse("department-detail", kwargs={"pk": department.id})
        update_data = {
            "department_code": "DEPT-001",
            "department_name": "Updated Department Name",
            "department_type": "PRODUCTION",
            "plant": str(department.plant.id) if department.plant else None,
            "status": "Active",
        }
        response = authenticated_client.put(url, update_data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        assert department.department_name == "Updated Department Name"

    def test_update_department_patch(self, authenticated_client, department):
        """Test partial update of department (PATCH)"""
        url = reverse("department-detail", kwargs={"pk": department.id})
        update_data = {"department_name": "Patched Department Name"}
        response = authenticated_client.patch(url, update_data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        assert department.department_name == "Patched Department Name"

    def test_delete_department(self, authenticated_client, department):
        """Test soft deleting a department (archive) - must be inactive first"""
        # First deactivate the department (required for archiving)
        department.status = "Inactive"
        department.save()
        url = reverse("department-detail", kwargs={"pk": department.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        assert department.is_archived is True

    def test_cannot_edit_archived_department(self, authenticated_client, department):
        """Test cannot edit archived department"""
        department.is_archived = True
        department.save()
        url = reverse("department-detail", kwargs={"pk": department.id})
        update_data = {"department_name": "Should Fail"}
        response = authenticated_client.patch(url, update_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_status_to_inactive(self, authenticated_client, department):
        """Test changing department status to inactive"""
        url = reverse("department-change-status", kwargs={"pk": department.id})
        response = authenticated_client.post(url, {"status": "Inactive"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        assert department.status == "Inactive"

    def test_change_status_to_active(self, authenticated_client, department):
        """Test changing department status to active"""
        department.status = "Inactive"
        department.save()
        url = reverse("department-change-status", kwargs={"pk": department.id})
        response = authenticated_client.post(url, {"status": "Active"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        assert department.status == "Active"

    def test_change_status_invalid(self, authenticated_client, department):
        """Test changing status with invalid value"""
        url = reverse("department-change-status", kwargs={"pk": department.id})
        response = authenticated_client.post(url, {"status": "Invalid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_status_missing_field(self, authenticated_client, department):
        """Test changing status without status field"""
        url = reverse("department-change-status", kwargs={"pk": department.id})
        response = authenticated_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_dropdown_api(self, authenticated_client, department):
        """Test dropdown API returns lightweight data"""
        url = reverse("department-dropdown")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        if len(response.data["data"]) > 0:
            assert "id" in response.data["data"][0]
            assert "department_code" in response.data["data"][0]
            assert "department_name" in response.data["data"][0]
            # Should not include other fields
            assert "cost_center_code" not in response.data["data"][0]
            assert "created_at" not in response.data["data"][0]

    def test_dropdown_api_with_plant_filter(
        self, authenticated_client, department, plant
    ):
        """Test dropdown API with plant filter"""
        url = reverse("department-dropdown")
        response = authenticated_client.get(url, {"plant_id": str(plant.id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_dropdown_api_only_active(self, authenticated_client, department):
        """Test dropdown API only returns active departments"""
        department.status = "Inactive"
        department.save()
        url = reverse("department-dropdown")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Inactive department should not appear
        dept_ids = [d["id"] for d in response.data["data"]]
        assert str(department.id) not in dept_ids

    def test_unauthorized_access(self, api_client):
        """Test unauthorized access returns 401"""
        url = reverse("department-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_archive_active_department(self, authenticated_client, department):
        """Test cannot archive active department - must deactivate first"""
        assert department.status == "Active"  # Ensure it's active
        url = reverse("department-detail", kwargs={"pk": department.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active" in response.data.get("message", "").lower()
        department.refresh_from_db()
        assert department.is_archived is False  # Should not be archived

    def test_can_archive_inactive_department(self, authenticated_client, department):
        """Test can archive inactive department"""
        # First deactivate the department
        department.status = "Inactive"
        department.save()
        url = reverse("department-detail", kwargs={"pk": department.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        department.refresh_from_db()
        assert department.is_archived is True

    def test_cannot_archive_with_active_children(
        self, authenticated_client, department, plant, user
    ):
        """Test cannot archive department with active child departments"""
        # First deactivate the department
        department.status = "Inactive"
        department.save()
        # Create child department
        child = Department.objects.create(
            department_code="DEPT-CHILD",
            department_name="Child Department",
            department_type="PRODUCTION",
            plant=plant,
            parent_department=department,
            status="Active",
            created_by=user,
            updated_by=user,
        )
        url = reverse("department-detail", kwargs={"pk": department.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "child" in response.data.get("message", "").lower()

    def test_can_archive_without_children(self, authenticated_client, department):
        """Test can archive inactive department without children"""
        # First deactivate the department
        department.status = "Inactive"
        department.save()
        url = reverse("department-detail", kwargs={"pk": department.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        department.refresh_from_db()
        assert department.is_archived is True

    def test_list_archived_departments(self, authenticated_client, department):
        """Test listing archived departments"""
        department.is_archived = True
        department.save()
        url = reverse("department-archived")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_get_archived_department(self, authenticated_client, department):
        """Test getting archived department details"""
        department.is_archived = True
        department.save()
        url = reverse("department-archived", kwargs={"pk": department.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["id"] == str(department.id)

    def test_bulk_archive_departments(
        self, authenticated_client, department, plant, user
    ):
        """Test bulk archive departments"""
        # Deactivate departments first (required for archiving)
        department.status = "Inactive"
        department.save()
        # Create another department
        dept2 = Department.objects.create(
            department_code="DEPT-002",
            department_name="Dept 2",
            department_type="PRODUCTION",
            plant=plant,
            status="Inactive",  # Must be inactive to archive
            created_by=user,
            updated_by=user,
        )
        url = reverse("department-bulk-archive")
        response = authenticated_client.post(
            url, {"ids": [str(department.id), str(dept2.id)]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        dept2.refresh_from_db()
        assert department.is_archived is True
        assert dept2.is_archived is True

    def test_bulk_archive_active_departments_fails(
        self, authenticated_client, department, plant, user
    ):
        """Test bulk archive fails for active departments"""
        # Create another active department
        dept2 = Department.objects.create(
            department_code="DEPT-002",
            department_name="Dept 2",
            department_type="PRODUCTION",
            plant=plant,
            status="Active",
            created_by=user,
            updated_by=user,
        )
        url = reverse("department-bulk-archive")
        response = authenticated_client.post(
            url, {"ids": [str(department.id), str(dept2.id)]}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active" in response.data.get("message", "").lower()

    def test_bulk_restore_departments(
        self, authenticated_client, department, plant, user
    ):
        """Test bulk restore departments"""
        # Archive departments
        department.is_archived = True
        department.save()
        dept2 = Department.objects.create(
            department_code="DEPT-002",
            department_name="Dept 2",
            department_type="PRODUCTION",
            plant=plant,
            status="Active",
            is_archived=True,
            created_by=user,
            updated_by=user,
        )
        url = reverse("department-bulk-restore")
        response = authenticated_client.post(
            url, {"ids": [str(department.id), str(dept2.id)]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        department.refresh_from_db()
        dept2.refresh_from_db()
        assert department.is_archived is False
        assert dept2.is_archived is False

    def test_bulk_archive_invalid_ids(self, authenticated_client):
        """Test bulk archive with invalid IDs"""
        url = reverse("department-bulk-archive")
        response = authenticated_client.post(url, {"ids": []}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_parent_department_validation_same_plant(
        self, authenticated_client, plant, parent_department, user
    ):
        """Test parent department must be in same plant"""
        url = reverse("department-list")
        data = {
            "department_code": "DEPT-CHILD",
            "department_name": "Child Department",
            "department_type": "PRODUCTION",
            "plant": str(plant.id),
            "parent_department": str(parent_department.id),
            "status": "Active",
        }
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_parent_department_cannot_be_self(self, authenticated_client, department):
        """Test department cannot be its own parent"""
        url = reverse("department-detail", kwargs={"pk": department.id})
        data = {
            "department_code": department.department_code,
            "department_name": department.department_name,
            "department_type": department.department_type,
            "plant": str(department.plant.id) if department.plant else None,
            "parent_department": str(department.id),
            "status": department.status,
        }
        response = authenticated_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_pagination(self, authenticated_client):
        """Test pagination works"""
        # Create multiple departments
        user = User.objects.first()
        plant = Plant.objects.first()
        if plant:
            for i in range(15):
                Department.objects.create(
                    department_code=f"DEPT-{i:03d}",
                    department_name=f"Department {i}",
                    department_type="PRODUCTION",
                    plant=plant,
                    status="Active",
                    created_by=user,
                    updated_by=user,
                )
        url = reverse("department-list")
        response = authenticated_client.get(url, {"pagesize": 10})
        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data["data"]
        assert "next" in response.data["data"]
        assert "previous" in response.data["data"]
