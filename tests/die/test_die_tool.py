import pytest
from django.urls import reverse
from rest_framework import status

from die.models import Die, DieTool, DieType


@pytest.mark.django_db
def test_list_die_tool(authenticated_api_client):
    die_type = DieType.objects.create(name="d4", description="Sample Die")
    die = Die.objects.create(die_number="Die1", die_type=die_type)

    # Create some test dies tools
    DieTool.objects.bulk_create(
        [
            DieTool(die=die, tool_number="001"),
            DieTool(die=die, tool_number="002"),
            DieTool(die=die, tool_number="003"),
        ]
    )
    url = reverse("die_tool-list")
    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]["data"]) == 3


@pytest.mark.django_db
def test_list_die_tool_with_search(authenticated_api_client):
    die_type = DieType.objects.create(name="d4", description="Sample Die")
    die = Die.objects.create(die_number="Die1", die_type=die_type)

    # Create some test dies tools
    DieTool.objects.bulk_create(
        [
            DieTool(die=die, tool_number="001"),
            DieTool(die=die, tool_number="002"),
            DieTool(die=die, tool_number="003"),
        ]
    )

    url = reverse("die_tool-list") + "?search=002"
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]["data"]) == 1


@pytest.mark.django_db
def test_list_die_tool_with_ordering(authenticated_api_client):
    die_type = DieType.objects.create(name="d4", description="Sample Die")
    die = Die.objects.create(die_number="Die1", die_type=die_type)

    # Create some test dies tools
    DieTool.objects.bulk_create(
        [
            DieTool(die=die, tool_number="001"),
            DieTool(die=die, tool_number="002"),
            DieTool(die=die, tool_number="003"),
        ]
    )

    url = reverse("die_tool-list") + "?ordering=die_type"
    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"]["data"][0]["tool_number"] == "003"


@pytest.mark.django_db
def test_create_die_tool(authenticated_api_client):
    url = reverse("die_tool-list")
    die_type = DieType.objects.create(name="d4", description="Sample Die")
    die = Die.objects.create(die_number="Die1", die_type=die_type)
    data = {
        "die": die.id,  # type: ignore
        "tool_number": "Tool 001",
    }
    response = authenticated_api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert DieTool.objects.filter(tool_number="Tool 001").exists()


@pytest.mark.django_db
def test_update_die_tool(authenticated_api_client):
    die_type = DieType.objects.create(name="d4", description="Sample Die")
    die = Die.objects.create(die_number="Die1", die_type=die_type)
    die_tool = DieTool.objects.create(die=die, tool_number="tool_001")
    url = reverse("die_tool-detail", args=[die_tool.id])  # type: ignore
    data = {
        "die": die.id,  # type: ignore
        "tool_number": "updated tool 001",
    }
    response = authenticated_api_client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert DieTool.objects.filter(tool_number="updated tool 001").exists()


@pytest.mark.django_db
def test_delete_die_tool(authenticated_api_client):
    die_type = DieType.objects.create(name="d4", description="Sample Die")
    die = Die.objects.create(die_number="Die1", die_type=die_type)

    # Create some test dies tools
    die_tool = DieTool.objects.create(die=die, tool_number="001")
    url = reverse("die_tool-detail", args=[die_tool.id])  # type: ignore
    response = authenticated_api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not DieTool.objects.filter(tool_number="001", deleted=0).exists()
