import factory
from factory import Faker

from common.models import Country, Currency, FinancialYearModel
from tests.model_factory.common_function import generate_limited_length_word


class FinancialYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FinancialYearModel

    financial_year = Faker("year")
    start_date = factory.Faker("date_between", start_date="-2y", end_date="today")
    end_date = factory.Faker("date_between", start_date="today", end_date="+2y")


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country

    name = Faker("country")
    code = Faker("country_code")
    unicode = factory.LazyFunction(lambda: generate_limited_length_word(max_length=80))
    country_flag = Faker("image_url", category="flags")
    phone_code = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=5)
    )


class CurrencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Currency

    country = factory.SubFactory(CountryFactory)
    currency_name = Faker("currency_name")
    currency_code = Faker("currency_code")
    currency_symbol = Faker("currency_symbol")
