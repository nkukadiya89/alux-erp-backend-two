import pytest

from common.models import Country, Currency


@pytest.fixture
def create_country():
    country = Country.objects.create(
        name="India", code="+91", unicode="+91", country_flag="indian_flag"
    )
    return country


@pytest.fixture
def create_currency(create_country):
    country = create_country
    Currency.objects.create(
        country=country,
        currency_name="Indian Rupee",
        currency_code="inr",
        currency_symbol="inr",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url,expected_status_code",
    [
        ("currency/", 200),
        ("currency/?id=1", 200),
        ("currency/?currency_name=Indian Rupee", 200),
        ("currency/?currency_code=inr", 200),
    ],
)
def test_get_country(
    authenticated_api_client, create_currency, api_base_url, url, expected_status_code
):
    response = authenticated_api_client.get(api_base_url + url)
    assert response.status_code == expected_status_code
