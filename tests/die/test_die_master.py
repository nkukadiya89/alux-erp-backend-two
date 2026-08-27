import pytest
from django.urls import reverse
from rest_framework import status

from die.models import DieCategory, DieGroup, DiePress, DieSize, DieSubCategory, DieType


@pytest.fixture(
    params=[
        (DieType, "die_type-list", "name"),
        (DieCategory, "die_category-list", "name"),
        (DieGroup, "die_group-list", "name"),
        (DieSize, "die_size-list", "die_size"),
        (DieSubCategory, "die_subcategory-list", "name"),
        (DiePress, "die_press-list", "name"),
        # Add more model and URL pairs as needed
    ]
)
def model_url_colname(request):
    return request.param


@pytest.mark.django_db
def test_list_dies(authenticated_api_client, model_url_colname):
    model, url, colname = model_url_colname
    # Create some test dies
    model.objects.bulk_create(
        [
            model(**{colname: "Sample Val 1", "description": "Sample Description"}),
            model(**{colname: "Sample Val 2", "description": "Sample Description"}),
            model(**{colname: "Sample Val 3", "description": "Sample Description"}),
        ]
    )

    url = reverse(url)
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]["data"]) == 3


@pytest.mark.django_db
def test_list_dies_with_search(authenticated_api_client, model_url_colname):
    model, url, colname = model_url_colname
    # Create some test dies
    model.objects.bulk_create(
        [
            model(**{colname: "Sample_Val_1", "description": "Sample Description"}),
            model(**{colname: "Sample_Val_2", "description": "Sample Description"}),
            model(**{colname: "Sample_Val_3", "description": "Sample Description"}),
        ]
    )

    url = reverse(url) + "?search=Sample_Val_1"
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]["data"]) == 1


@pytest.mark.django_db
def test_list_dies_with_ordering(authenticated_api_client, model_url_colname):
    model, url, colname = model_url_colname
    model.objects.bulk_create(
        [
            model(**{colname: "Sample_Val_1", "description": "Sample Description"}),
            model(**{colname: "Sample_Val_2", "description": "Sample Description"}),
            model(**{colname: "Sample_Val_3", "description": "Sample Description"}),
        ]
    )

    url = reverse(url) + f"?ordering=-{colname}"
    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"]["data"][0][colname] == "Sample_Val_3"


@pytest.mark.django_db
def test_create_die(authenticated_api_client, model_url_colname):
    model, url, colname = model_url_colname
    url = reverse(url)
    data = {
        colname: "Sample_Val_2",
        "description": "Sample description",
    }
    response = authenticated_api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert model.objects.filter(**{colname: "Sample_Val_2"}).exists()


@pytest.mark.django_db
def test_update_die(authenticated_api_client, model_url_colname):
    model, url, colname = model_url_colname
    # url = url.split("-")[0] + "-detail"
    # url = reverse(url)
    # print("reversed_url" ,url)
    model_instance = model.objects.create(
        **{colname: "Sample_val", "description": "description defined"}
    )
    # url = reverse(url, args=[model_instance.id]) # type: ignore
    detail_url = reverse(f"{url[:-5]}-detail", args=[model_instance.id])
    data = {
        colname: "Val Updated",
        "description": "sample desc",
    }
    response = authenticated_api_client.patch(detail_url, data, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert model.objects.filter(**{colname: "Val Updated"}).exists()


@pytest.mark.django_db
def test_delete_die(authenticated_api_client, model_url_colname):
    model, url, colname = model_url_colname
    model_instance = model.objects.create(
        **{colname: "Sample_val", "description": "description defined"}
    )
    detail_url = reverse(f"{url[:-5]}-detail", args=[model_instance.id])
    response = authenticated_api_client.delete(detail_url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not model.objects.filter(**{colname: "Val Updated"}).exists()
