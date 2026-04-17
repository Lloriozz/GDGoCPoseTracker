from __future__ import annotations

import re

from app.core.text_utils import normalize_text
from app.schemas.user_profile import UserProfilePatch


GOAL_KEYWORDS = {
    "muscle_gain": ["tang co", "len co", "build muscle", "gain muscle"],
    "fat_loss": ["giam mo", "giam can", "cut", "fat loss"],
    "maintenance": ["duy tri", "giu can", "maintenance"],
    "recomp": ["recomp", "vua tang co vua giam mo", "siet co"],
}

ACTIVITY_KEYWORDS = {
    "low": ["it van dong", "rat it van dong", "sedentary"],
    "light": ["van dong nhe", "tap nhe", "light"],
    "moderate": ["moderate", "vua phai", "tap deu"],
    "high": ["cuong do cao", "van dong cao", "tap nhieu", "very active", "high"],
}


def extract_profile_patch_from_message(message: str) -> UserProfilePatch | None:
    normalized = normalize_text(message)
    payload: dict[str, object] = {}

    age_match = re.search(r"\b(\d{1,2})\s*tuoi\b", normalized)
    if age_match:
        payload["age"] = int(age_match.group(1))

    height_match = re.search(r"\bcao\s*(\d+(?:[.,]\d+)?)\s*cm\b", normalized)
    if height_match:
        payload["height_cm"] = float(height_match.group(1).replace(",", "."))

    weight_match = re.search(r"\bnang\s*(\d+(?:[.,]\d+)?)\s*kg\b", normalized)
    if weight_match:
        payload["weight_kg"] = float(weight_match.group(1).replace(",", "."))

    days_match = re.search(r"\b(?:tap\s*)?(\d{1,2})\s*buoi(?:\s*moi\s*tuan)?\b", normalized)
    if days_match:
        payload["workout_days_per_week"] = int(days_match.group(1))

    sex = _extract_sex(normalized)
    if sex:
        payload["sex"] = sex

    goal = _extract_goal(normalized)
    if goal:
        payload["goal"] = goal

    train_location = _extract_train_location(normalized)
    if train_location:
        payload["train_location"] = train_location

    activity_level = _extract_activity_level(normalized, payload.get("workout_days_per_week"))
    if activity_level:
        payload["activity_level"] = activity_level

    if not payload:
        return None
    return UserProfilePatch(**payload)


def merge_profile_patches(
    inferred_patch: UserProfilePatch | None,
    explicit_patch: UserProfilePatch | None,
) -> UserProfilePatch | None:
    if inferred_patch is None and explicit_patch is None:
        return None

    merged_payload: dict[str, object] = {}
    if inferred_patch is not None:
        merged_payload.update(inferred_patch.model_dump(exclude_none=True))
    if explicit_patch is not None:
        merged_payload.update(explicit_patch.model_dump(exclude_none=True))
    return UserProfilePatch(**merged_payload)


def _extract_sex(normalized: str) -> str | None:
    if re.search(r"\b(toi|minh|la)\s+nam\b", normalized) or "gioi tinh nam" in normalized:
        return "male"
    if re.search(r"\b(toi|minh|la)\s+nu\b", normalized) or "gioi tinh nu" in normalized:
        return "female"
    if "male" in normalized:
        return "male"
    if "female" in normalized:
        return "female"
    return None


def _extract_goal(normalized: str) -> str | None:
    for goal, keywords in GOAL_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return goal
    return None


def _extract_train_location(normalized: str) -> str | None:
    if any(keyword in normalized for keyword in ["o gym", "tai gym", "phong gym", "tap gym"]):
        return "gym"
    if any(keyword in normalized for keyword in ["o nha", "tai nha", "tap tai nha", "home workout"]):
        return "home"
    return None


def _extract_activity_level(normalized: str, workout_days_per_week: object) -> str | None:
    for activity_level, keywords in ACTIVITY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return activity_level

    if isinstance(workout_days_per_week, int):
        if workout_days_per_week >= 5:
            return "high"
        if workout_days_per_week >= 3:
            return "moderate"
        if workout_days_per_week >= 1:
            return "light"
    return None
