import factory
from factory import Faker

from tests.model_factory.common_function import generate_limited_length_word
from user.models import User, UserProfile


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "defaultpassword")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    phone = Faker("phone_number")
    is_active = True
    status = "active"
    keep_me_logged_in = False


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    profile_image = Faker("image_url")
    designation = Faker("job")
    message = "This is a default message"
    role = factory.LazyFunction(lambda: generate_limited_length_word(max_length=15))
    whatsapp_verified = False
    aadhar_card = factory.Sequence(lambda n: f"AADHAR{n:012d}")
    pancard = factory.Sequence(lambda n: f"PANCARD{n:010d}")
    emergency_contact = Faker("phone_number")
    current_address = Faker("address")
    permanent_address = Faker("address")
    email_verified = False
    phone_verified = False
    password_last_changed = None
