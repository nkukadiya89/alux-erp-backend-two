import random
import string


def generate_random_password():
    password_length = 10
    # Define allowed special characters explicitly
    allowed_specials = "#$%&()*+-./:<=>?@[]^_{|}"
    characters = string.ascii_letters + string.digits + allowed_specials
    random_password = "".join(random.choice(characters) for _ in range(password_length))
    return random_password
