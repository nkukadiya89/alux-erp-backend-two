import factory
from factory import Faker

from quotation.models import Quotation, QuotationDetail
from tests.model_factory.common_function import generate_limited_length_word
from tests.model_factory.die_factories import ConversionRateFactory, DieFactory
from tests.model_factory.party_factories import PartyFactory
from tests.model_factory.product_factories import AlloyFactory, TemperFactory


class QuotationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Quotation

    quotation_no = Faker("bothify", text="QT-#######")
    party = factory.SubFactory(PartyFactory)
    due_date = factory.Faker("date")
    payment_terms = Faker("sentence", nb_words=6)
    delay_days = Faker("random_int", min=0, max=30)
    delivery_schedule = Faker("random_int", min=1, max=10)
    validity = factory.LazyFunction(lambda: generate_limited_length_word(max_length=25))
    remarks = Faker("paragraph", nb_sentences=2)
    weight_range = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )


class QuotationDetailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QuotationDetail

    quotation = factory.SubFactory(QuotationFactory)
    die_profile = factory.SubFactory(DieFactory)
    alloy = factory.SubFactory(AlloyFactory)
    temper = factory.SubFactory(TemperFactory)
    length = factory.Faker("random_float", min=0.1, max=100.0, decimal_places=2)
    net_weight = factory.Faker("random_float", min=0.1, max=100.0, decimal_places=2)
    pieces = factory.Faker("random_int", min=1, max=100)
    surface_finish = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    price_per_kg = factory.Faker("random_float", min=10.0, max=100.0, decimal_places=2)
    conversion = factory.SubFactory(
        ConversionRateFactory
    )  # Assuming ConversionRateFactory is defined
    anodize_rate = factory.Faker("random_float", min=0.0, max=10.0, decimal_places=2)
