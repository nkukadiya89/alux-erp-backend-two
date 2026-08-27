import factory
from factory import Faker, SubFactory

from die.models import (
    ConversionRate,
    Die,
    DieCategory,
    DieGroup,
    DiePress,
    DieSize,
    DieSubCategory,
    DieType,
)
from tests.model_factory.common_function import generate_limited_length_word
from tests.model_factory.party_factories import PartyFactory
from tests.model_factory.product_factories import AlloyFactory, TemperFactory


class DiePressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiePress

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
    description = Faker("sentence")


class DieGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DieGroup

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
    description = Faker("sentence")


class DieCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DieCategory

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
    description = Faker("sentence")


class DieSubCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DieSubCategory

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
    description = Faker("sentence")


class DieTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DieType

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
    description = Faker("sentence")


class DieSizeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DieSize

    die_size = factory.LazyFunction(lambda: generate_limited_length_word(max_length=25))
    description = Faker("sentence")


class DieFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Die
        skip_postgeneration_save = True

    die_number = Faker("random_int", min=1, max=1000)
    dimension1 = Faker("random_number", digits=5, fix_len=True)
    dimension2 = Faker("random_number", digits=5, fix_len=True)
    dimension3 = Faker("random_number", digits=5, fix_len=True)
    dimension4 = Faker("random_number", digits=5, fix_len=True)
    wt_kg_p_mt = Faker("random_number", digits=5, fix_len=True)
    die_group = SubFactory(DieGroupFactory)
    die_category = SubFactory(DieCategoryFactory)
    die_sub_category = SubFactory(DieSubCategoryFactory)
    eligible_for_press = factory.post_generation(
        lambda obj, create, extracted, **kwargs: [DiePressFactory() for _ in range(2)]
    )
    die_type = SubFactory(DieTypeFactory)
    die_diagram = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=250)
    )
    die_detail_diagram = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=250)
    )
    customer_approved_diagram = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=250)
    )
    autocad_drawing = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=250)
    )
    die_manufacturing = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=250)
    )
    total_running_qty = Faker("random_number", digits=5, fix_len=True)
    total_running_ton = Faker("random_number", digits=5, fix_len=True)
    remarks = Faker("sentence")


class ConversionRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConversionRate

    party = factory.SubFactory(PartyFactory)
    die = factory.SubFactory(DieFactory)
    conversion = factory.Faker("random_number", digits=2)
    packing_cost = factory.Faker("random_number", digits=2)
    alloy = factory.SubFactory(AlloyFactory)
    temper = factory.SubFactory(TemperFactory)
    remarks = factory.Faker("text")
