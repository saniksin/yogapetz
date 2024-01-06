import re


def validate_token(input_string: str) -> str | None:
    word_pattern = r'^[a-z0-9]{40}$'
    words = re.split(r'[\s,:;.()\[\]{}<>]', input_string)

    for word in words:
        if re.match(word_pattern, word):
            return word

    return None