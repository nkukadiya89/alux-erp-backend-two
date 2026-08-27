import random
import uuid

import factory
from factory import Faker

from party.models import Party
from tests.model_factory.common_function import generate_limited_length_word


def generate_bank_account_number(instance):
    return "".join(
        [str(random.randint(0, 9)) for _ in range(10)]
    )  # Generates a random 10-digit number


class PartyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Party

    name = factory.LazyFunction(lambda: generate_limited_length_word(max_length=150))
    sundry_group = factory.Iterator(["sundry_creditors", "sundry_debtors"])
    account_group = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    customer_category = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    customer_subcategory = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    customer_type = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    office_address = Faker("address")
    registered_address = Faker("address")
    shipping_address = Faker("address")
    applicable_gst = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    party_section_no = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=50)
    )
    bank_name = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    bank_branch_name = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    bank_branch_address = Faker("address")
    bank_ifsc_code = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=15)
    )
    gst_no = factory.LazyFunction(lambda: generate_limited_length_word(max_length=25))
    gst_type = factory.LazyFunction(lambda: generate_limited_length_word(max_length=25))
    pan_number = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=15)
    )
    udhyam_no = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    sgst_number = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    cgst_number = factory.LazyFunction(
        lambda: generate_limited_length_word(max_length=25)
    )
    unique_id = factory.LazyFunction(
        lambda: str(uuid.uuid4()) + str(random.randint(0, 999999))
    )  # Generate a unique ID
