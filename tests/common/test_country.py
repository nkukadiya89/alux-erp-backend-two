import pytest

from common.models import Country


@pytest.fixture
def create_country():
    country = Country.objects.create(
        name="India", code="+91", unicode="+91", country_flag="indian_flag"
    )
    return country


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url,expected_status_code",
    [
        ("country/", 200),
        ("country/?id=1", 200),
        ("country/?name=India", 200),
        ("country/?code=+91", 200),
    ],
)
def test_get_country(
    authenticated_api_client, create_country, api_base_url, url, expected_status_code
):
    response = authenticated_api_client.get(api_base_url + url)
    assert response.status_code == expected_status_code
