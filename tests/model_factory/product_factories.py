import factory

from product.models import Alloy, Temper
from tests.model_factory.common_function import generate_limited_length_word


class AlloyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Alloy

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=25))
    color_code = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=50)
    )
    ingredient = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    application = factory.Faker("sentence", nb_words=6)
    remark = factory.Faker("sentence", nb_words=10)


class TemperFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Temper

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=25))
    code = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
