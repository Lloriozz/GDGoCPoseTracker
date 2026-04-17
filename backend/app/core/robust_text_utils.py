from __future__ import annotations

import unicodedata

from app.core.text_utils import normalize_text


SUSPICIOUS_MOJIBAKE_MARKERS = (
    "Ã",
    "Ä",
    "áº",
    "á»",
    "Â",
    "Ð",
    "Ñ",
    "â",
    "€™",
    "œ",
    "š",
    "ƒ",
    "‹",
    "›",
)

WEIRD_CP1252_CHARS = {"ƒ", "‹", "›", "€", "™", "œ", "ž"}


CP1252_REVERSE_MAP = {
    "\u20ac": 0x80,
    "\u201a": 0x82,
    "\u0192": 0x83,
    "\u201e": 0x84,
    "\u2026": 0x85,
    "\u2020": 0x86,
    "\u2021": 0x87,
    "\u02c6": 0x88,
    "\u2030": 0x89,
    "\u0160": 0x8A,
    "\u2039": 0x8B,
    "\u0152": 0x8C,
    "\u017d": 0x8E,
    "\u2018": 0x91,
    "\u2019": 0x92,
    "\u201c": 0x93,
    "\u201d": 0x94,
    "\u2022": 0x95,
    "\u2013": 0x96,
    "\u2014": 0x97,
    "\u02dc": 0x98,
    "\u2122": 0x99,
    "\u0161": 0x9A,
    "\u203a": 0x9B,
    "\u0153": 0x9C,
    "\u017e": 0x9E,
    "\u0178": 0x9F,
}


def repair_mojibake(value: str) -> str:
    if not any(marker in value for marker in SUSPICIOUS_MOJIBAKE_MARKERS):
        return value

    repaired = value
    for _ in range(2):
        candidate = _repair_once(repaired)
        if candidate == repaired:
            break
        repaired = candidate
    return repaired


def robust_normalize_text(value: str) -> str:
    return normalize_text(repair_mojibake(value))


def _repair_once(value: str) -> str:
    candidates = [value]
    remapped_bytes = _to_probable_source_bytes(value)
    if remapped_bytes is not None:
        try:
            repaired = remapped_bytes.decode("utf-8")
        except UnicodeDecodeError:
            repaired = ""
        if repaired and repaired != value:
            candidates.append(repaired)

    for source_encoding in ("cp1252", "latin1"):
        try:
            repaired = value.encode(source_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired and repaired != value:
            candidates.append(repaired)

    best = min(candidates, key=_score_text)
    return best if _score_text(best) < _score_text(value) else value


def _score_text(value: str) -> int:
    marker_hits = sum(value.count(marker) for marker in SUSPICIOUS_MOJIBAKE_MARKERS)
    weird_chars = sum(
        1
        for char in value
        if char in WEIRD_CP1252_CHARS or unicodedata.category(char).startswith("C")
    )
    return marker_hits * 4 + weird_chars


def _to_probable_source_bytes(value: str) -> bytes | None:
    raw_bytes = bytearray()
    for char in value:
        codepoint = ord(char)
        if codepoint <= 0xFF:
            raw_bytes.append(codepoint)
            continue

        mapped = CP1252_REVERSE_MAP.get(char)
        if mapped is None:
            return None
        raw_bytes.append(mapped)
    return bytes(raw_bytes)
