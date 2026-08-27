import json

import pytest
from django.urls import reverse
from rest_framework import status

from die.models import Die, DieType
from tests.model_factory import die_factories


@pytest.mark.django_db
class TestDieViewSet:
    def test_list_dies(self, authenticated_api_client):
        die_factories.DieFactory.create_batch(3)

        url = reverse("die-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_dies_with_search(self, authenticated_api_client):
        # Create some test dies
        die_factories.DieFactory(die_number="0001")
        die_factories.DieFactory(die_number="0002")
        die_factories.DieFactory(die_number="0003")
        die_factories.DieFactory(die_number="0004")

        # die_number = die1.die_number
        url = reverse("die-list") + "?search=0001"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 1

    def test_list_dies_with_ordering(self, authenticated_api_client):
        die_factories.DieFactory(die_number="Die1")
        die_factories.DieFactory(die_number="Die2")
        die_factories.DieFactory(die_number="Die3")

        url = reverse("die-list") + "?ordering=-die_number"
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"]["data"][0]["die_number"] == "Die3"

    def test_create_die(self, authenticated_api_client):
        url = reverse("die-list")
        DieType.objects.create(name="d4", description="Sample Die")
        data = {
            "form_data": json.dumps(
                {
                    "die_number": "Die4",
                    "die_type_id": 1,
                }
            )
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Die.objects.filter(die_number="Die4").exists()

    def test_update_die(self, authenticated_api_client):
        die1 = die_factories.DieFactory()

        url = reverse("die-detail", args=[die1.id])  # type: ignore
        data = {
            "die_number": "Die1 Updated",
            "die_type_id": 1,
        }
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert Die.objects.filter(die_number="Die1 Updated").exists()

    def test_delete_die(self, authenticated_api_client):
        die1 = die_factories.DieFactory()

        die_number = die1.die_number
        url = reverse("die-detail", args=[die1.id])  # type: ignore
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Die.objects.filter(die_number=die_number, deleted=0).exists()
