import unicodedata


def normalize_text(value: str) -> str:
    lowered = value.lower().replace("đ", "d").replace("Ä‘", "d")
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(char for char in normalized if not unicodedata.combining(char))
