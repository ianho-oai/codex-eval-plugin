import re
import unicodedata


def slugify(text):
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')
