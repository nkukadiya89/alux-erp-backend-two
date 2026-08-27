import factory

from tests.model_factory.common_function import generate_limited_length_word
from tests.model_factory.die_factories import ConversionRateFactory, DieFactory
from tests.model_factory.party_factories import PartyFactory
from tests.model_factory.product_factories import AlloyFactory, TemperFactory
from workorder.models import WorkOrder, WorkOrderDetail


class WorkOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkOrder

    workorder_no = factory.Sequence(lambda n: f"WO-{n}")
    party = factory.SubFactory(PartyFactory)
    bill_to = factory.Faker("address")
    ship_to = factory.Faker("address")
    order_date = "2025-12-01"
    rate = factory.Faker("random_number", digits=5)
    delivery_date = "2025-12-01"
    tolerance = factory.Faker("random_int", min=0, max=10)
    purchase_order_no = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    purchase_order_date = factory.Faker("date_this_year")
    jobwork = factory.LazyFunction(lambda: generate_limited_length_word(max_length=50))
    remarks = factory.Faker("text")


class WorkOrderDetailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkOrderDetail

    workorder = factory.SubFactory(WorkOrderFactory)
    die_profile = factory.SubFactory(DieFactory)
    alloy = factory.SubFactory(AlloyFactory)
    temper = factory.SubFactory(TemperFactory)
    length = factory.Faker("random_number", digits=3)
    net_weight = factory.Faker("random_number", digits=3)
    pieces = factory.Faker("random_int", min=1, max=100)
    nalco_rate = factory.Faker("random_number", digits=5)
    conversion = factory.SubFactory(ConversionRateFactory)
    anodize_rate = factory.Faker("random_number", digits=5)
    packing_charge = factory.Faker("random_number", digits=5)
