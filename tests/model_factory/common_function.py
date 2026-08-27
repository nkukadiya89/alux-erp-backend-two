import random
import string


def generate_limited_length_word(max_length=10):
    # Generate a random word of length up to max_length
    length = random.randint(
        1, max_length
    )  # Choose a random length between 1 and max_length
    return "".join(
        random.choices(string.ascii_lowercase, k=length)
    )  # Generate a random word
