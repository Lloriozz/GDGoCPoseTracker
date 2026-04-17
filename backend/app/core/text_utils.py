import unicodedata


def _maybe_fix_mojibake(value: str) -> str:
    suspicious_markers = ("Ã", "Ä", "áº", "á»", "Â", "Ð", "Ñ")
    if not any(marker in value for marker in suspicious_markers):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if repaired else value


def normalize_text(value: str) -> str:
    repaired = _maybe_fix_mojibake(value)
    lowered = repaired.lower().replace("đ", "d").replace("Ä‘", "d").replace("Ã„â€˜", "d")
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(char for char in normalized if not unicodedata.combining(char))
