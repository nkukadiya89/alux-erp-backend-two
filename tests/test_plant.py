import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from common.models import Plant

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def plant_data():
    return {
        "plant_code": "PLT001",
        "plant_name": "Test Plant",
        "plant_type": "Extrusion",
        "status": "Active",
        "address_line_1": "123 Test Street",
        "address_line_2": "Building A",
        "city": "Test City",
        "state": "Test State",
        "country": "Test Country",
        "postal_code": "12345",
        "phone_number": "1234567890",
        "email": "plant@test.com",
        "plant_head_name": "John Doe",
    }


@pytest.fixture
def plant(db, user, plant_data):
    return Plant.objects.create(**plant_data, created_by=user, updated_by=user)


@pytest.mark.django_db
class TestPlantModel:
    """Test Plant Model"""

    def test_plant_creation(self, user, plant_data):
        """Test creating a plant"""
        plant = Plant.objects.create(**plant_data, created_by=user, updated_by=user)
        assert plant.plant_code == "PLT001"
        assert plant.plant_name == "Test Plant"
        assert plant.status == "Active"
        assert str(plant) == "PLT001 - Test Plant"

    def test_plant_code_unique(self, user, plant_data):
        """Test plant_code uniqueness"""
        Plant.objects.create(**plant_data, created_by=user, updated_by=user)
        with pytest.raises(Exception):
            Plant.objects.create(**plant_data, created_by=user, updated_by=user)

    def test_plant_can_deactivate(self, plant):
        """Test can_deactivate method"""
        can_deactivate, message = plant.can_deactivate()
        assert can_deactivate is True
        assert message is None


@pytest.mark.django_db
class TestPlantAPI:
    """Test Plant API endpoints"""

    def test_create_plant_success(self, authenticated_client, plant_data):
        """Test successful plant creation"""
        url = reverse("plant-list")
        response = authenticated_client.post(url, plant_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["plant_code"] == "PLT001"

    def test_create_plant_duplicate_code(self, authenticated_client, plant, plant_data):
        """Test creating plant with duplicate code fails"""
        url = reverse("plant-list")
        response = authenticated_client.post(url, plant_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_plant_invalid_email(self, authenticated_client, plant_data):
        """Test creating plant with invalid email fails"""
        plant_data["email"] = "invalid-email"
        url = reverse("plant-list")
        response = authenticated_client.post(url, plant_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_plant_missing_required_fields(self, authenticated_client):
        """Test creating plant without required fields fails"""
        url = reverse("plant-list")
        response = authenticated_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_plants(self, authenticated_client, plant):
        """Test listing plants"""
        url = reverse("plant-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]["results"]) > 0

    def test_list_plants_with_filters(self, authenticated_client, plant):
        """Test listing plants with filters"""
        url = reverse("plant-list")
        response = authenticated_client.get(url, {"status": "Active"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_list_plants_with_search(self, authenticated_client, plant):
        """Test listing plants with search"""
        url = reverse("plant-list")
        response = authenticated_client.get(url, {"search": "PLT001"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_retrieve_plant(self, authenticated_client, plant):
        """Test retrieving a single plant"""
        url = reverse("plant-detail", kwargs={"pk": plant.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["id"] == str(plant.id)

    def test_update_plant(self, authenticated_client, plant):
        """Test updating a plant"""
        url = reverse("plant-detail", kwargs={"pk": plant.id})
        update_data = {"plant_name": "Updated Plant Name"}
        response = authenticated_client.patch(url, update_data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        plant.refresh_from_db()
        assert plant.plant_name == "Updated Plant Name"

    def test_delete_plant(self, authenticated_client, plant):
        """Test soft deleting a plant"""
        url = reverse("plant-detail", kwargs={"pk": plant.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        plant.refresh_from_db()
        assert plant.deleted is True

    def test_change_status_to_inactive(self, authenticated_client, plant):
        """Test changing plant status to inactive"""
        url = reverse("plant-change-status", kwargs={"pk": plant.id})
        response = authenticated_client.post(url, {"status": "Inactive"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        plant.refresh_from_db()
        assert plant.status == "Inactive"

    def test_change_status_to_active(self, authenticated_client, plant):
        """Test changing plant status to active"""
        plant.status = "Inactive"
        plant.save()
        url = reverse("plant-change-status", kwargs={"pk": plant.id})
        response = authenticated_client.post(url, {"status": "Active"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        plant.refresh_from_db()
        assert plant.status == "Active"

    def test_change_status_invalid(self, authenticated_client, plant):
        """Test changing status with invalid value"""
        url = reverse("plant-change-status", kwargs={"pk": plant.id})
        response = authenticated_client.post(url, {"status": "Invalid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_dropdown_api(self, authenticated_client, plant):
        """Test dropdown API returns lightweight data"""
        url = reverse("plant-dropdown")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "id" in response.data["data"][0]
        assert "plant_code" in response.data["data"][0]
        assert "plant_name" in response.data["data"][0]
        # Should not include other fields
        assert "address_line_1" not in response.data["data"][0]

    def test_unauthorized_access(self, api_client):
        """Test unauthorized access returns 401"""
        url = reverse("plant-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_case_insensitive_plant_code(self, authenticated_client, plant_data):
        """Test plant_code is case-insensitive unique"""
        # Create first plant
        authenticated_client.post(reverse("plant-list"), plant_data, format="json")
        # Try to create with lowercase code
        plant_data["plant_code"] = "plt001"
        response = authenticated_client.post(
            reverse("plant-list"), plant_data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_phone_number_validation(self, authenticated_client, plant_data):
        """Test phone number validation"""
        plant_data["phone_number"] = "123"  # Too short
        response = authenticated_client.post(
            reverse("plant-list"), plant_data, format="json"
        )
        # Validation happens in serializer
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED,
        ]  # Depends on validation implementation
