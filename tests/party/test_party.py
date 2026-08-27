import pytest
from django.urls import reverse
from rest_framework import status

from party.models import Party
from tests.model_factory.party_factories import PartyFactory


@pytest.mark.django_db
def test_list_parties(authenticated_api_client):
    PartyFactory.create_batch(2)
    url = reverse("party-list")
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]["data"]) == 2


@pytest.mark.django_db
def test_create_party(authenticated_api_client):
    url = reverse("party-list")
    data = {
        "name": "Party 3",
        "sundry_group": "sundry_debtors",
        "account_group": "account_group",
        "customer_category": "customer_category",
        "customer_subcategory": "customer_subcategory",
        "customer_type": "customer_type",
        "party_section_no": "party_section_no",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Party.objects.count() == 1


@pytest.mark.django_db
def test_retrieve_party(authenticated_api_client):
    party = PartyFactory(name="Party 4", sundry_group="sundry_debtors")
    url = reverse("party-detail", args=[party.id])  # type: ignore
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Party 4"


@pytest.mark.django_db
def test_update_party(authenticated_api_client):
    party = PartyFactory(name="Party 5", sundry_group="sundry_debtors")
    url = reverse("party-detail", args=[party.id])  # type: ignore
    data = {
        "name": "Party 5 Updated",
        "sundry_group": "sundry_creditors",
        "account_group": "account_group",
        "customer_category": "customer_category",
        "customer_subcategory": "customer_subcategory",
        "customer_type": "customer_type",
        "party_section_no": "party_section_no",
    }
    response = authenticated_api_client.put(url, data, format="json")
    assert response.status_code == status.HTTP_202_ACCEPTED
    party.refresh_from_db()
    assert party.name == "Party 5 Updated"


@pytest.mark.django_db
def test_delete_party(authenticated_api_client):
    party = PartyFactory(name="Party 6", sundry_group="Sundry Group 6")
    url = reverse("party-detail", args=[party.id])  # type: ignore
    response = authenticated_api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Party.objects.count() == 1


@pytest.mark.django_db
def test_search_party(authenticated_api_client):
    party = PartyFactory()
    PartyFactory.create_batch(3)
    url = reverse("party-list")
    response = authenticated_api_client.get(url, {"search": party.name})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]["data"]) == 1


@pytest.mark.django_db
def test_ordering_party(authenticated_api_client):
    PartyFactory(name="Party 9", sundry_group="Sundry Group 9")
    PartyFactory(name="Party 10", sundry_group="Sundry Group 10")
    url = reverse("party-list")
    response = authenticated_api_client.get(url, {"ordering": "name"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"]["data"][0]["name"] == "Party 10"
