from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.text_utils import normalize_text
from app.schemas.user_profile import UserProfile


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "la",
    "gi",
    "toi",
    "minh",
    "ban",
    "cho",
    "va",
    "de",
    "nen",
    "neu",
    "thi",
    "nhu",
    "nao",
    "can",
    "co",
    "the",
    "hay",
    "mot",
    "nhung",
    "cac",
    "trong",
    "voi",
    "o",
    "nay",
    "kia",
    "do",
    "hoi",
    "lam",
    "giup",
    "gium",
    "an",
}

TOKEN_EXPANSIONS = {
    "tang": {"tang_co", "muscle_gain"},
    "tang_co": {"muscle_gain", "protein", "calories"},
    "muscle_gain": {"tang_co", "protein", "calories"},
    "giam_mo": {"fat_loss", "it_calorie", "no_lau"},
    "fat_loss": {"giam_mo", "it_calorie", "no_lau"},
    "tiet_kiem": {"budget_low", "gia_re", "chi_phi"},
    "gia_re": {"budget_low", "tiet_kiem", "chi_phi"},
    "chi_phi": {"budget_low", "tiet_kiem", "gia_re"},
    "quick": {"nhanh", "prep_nhanh", "it_thoi_gian"},
    "nhanh": {"quick", "prep_nhanh", "it_thoi_gian"},
    "an_chay": {"vegetarian", "plant_protein", "dau_hu", "dau_nanh"},
    "vegetarian": {"an_chay", "plant_protein", "dau_hu", "dau_nanh"},
    "khong_sua": {"dairy_free", "lactose_free", "sua_dau_nanh"},
    "dairy_free": {"khong_sua", "lactose_free", "sua_dau_nanh"},
    "knee": {"dau_goi", "lower_body", "rom", "hip_hinge"},
    "dau_goi": {"knee", "lower_body", "rom", "hip_hinge"},
    "shoulder": {"vai", "upper_body", "face_pull"},
    "vai": {"shoulder", "upper_body", "face_pull"},
    "home": {"o_nha", "dumbbell", "bodyweight"},
    "gym": {"may_tap", "barbell", "cable"},
    "protein": {"no_lau", "giu_co"},
    "recovery": {"hoi_phuc", "ngu", "ngay_nghi"},
    "hoi_phuc": {"recovery", "ngu", "ngay_nghi"},
    "pho": {"bun", "com", "mon_viet"},
    "bun": {"pho", "com", "mon_viet"},
    "com": {"pho", "bun", "mon_viet"},
}

CATEGORY_SIGNAL_TOKENS = {
    "meal_budget": {"budget_low", "tiet", "kiem", "gia", "re", "chi", "phi"},
    "meal_quick": {"quick", "nhanh", "prep_nhanh", "it_thoi_gian"},
    "meal_structure": {"protein", "chia", "bua"},
    "meal_substitution": {"thay", "mon", "substitute", "dairy_free", "khong_sua"},
    "meal_vietnamese": {"pho", "bun", "com", "mon_viet"},
    "meal_constraint_vegetarian": {"vegetarian", "an_chay", "plant_protein"},
    "meal_constraint_dairy_free": {"dairy_free", "khong_sua", "lactose_free"},
    "meal_goal_muscle_gain": {"muscle_gain", "tang_co", "calories", "carb"},
    "meal_goal_fat_loss": {"fat_loss", "giam_mo", "it_calorie", "no_lau"},
    "workout_beginner": {"beginner", "nguoi_moi"},
    "workout_progression": {"progressive", "overload", "progressive_overload"},
    "recovery_basics": {"recovery", "hoi_phuc", "ngu", "ngay_nghi"},
    "workout_injury_knee": {"knee", "dau_goi", "rom", "hip_hinge"},
    "workout_injury_shoulder": {"shoulder", "vai", "face_pull"},
    "workout_home": {"home", "o_nha", "bodyweight", "dumbbell"},
}

CATEGORY_SIGNAL_BONUS = {
    "meal_budget": 8,
    "meal_quick": 6,
    "meal_constraint_vegetarian": 8,
    "meal_constraint_dairy_free": 8,
    "meal_vietnamese": 5,
    "workout_injury_knee": 8,
    "workout_injury_shoulder": 8,
    "workout_home": 6,
    "workout_beginner": 5,
    "workout_progression": 6,
}


@dataclass(slots=True)
class KnowledgeEntry:
    id: str
    title: str
    content: str
    intents: list[str]
    tags: list[str]
    category: str = ""
    profile_tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


class KnowledgeRetriever:
    def __init__(
        self,
        kb_path: str | None = None,
        top_k: int | None = None,
        min_score: int | None = None,
    ) -> None:
        self.kb_path = Path(kb_path or settings.kb_path)
        self.top_k = top_k or settings.rag_top_k
        self.min_score = min_score or settings.rag_min_score
        self._entries = self._load_entries()

    def retrieve(
        self,
        message: str,
        intent: str,
        profile: UserProfile,
        allowed_category_prefixes: tuple[str, ...] | None = None,
    ) -> list[dict[str, object]]:
        if not settings.rag_enabled or not self._entries:
            return []

        message_tokens = self._expand_tokens(self._tokenize(message))
        profile_tokens = self._expand_tokens(self._build_profile_hint_tokens(profile, intent))
        if allowed_category_prefixes is None:
            allowed_category_prefixes = self._allowed_category_prefixes(intent)
        if not message_tokens and not profile_tokens:
            return []

        scored_entries: list[tuple[int, KnowledgeEntry]] = []
        for entry in self._entries:
            if not self._is_entry_allowed_for_intent(entry, allowed_category_prefixes):
                continue
            score = self._score_entry(entry, message_tokens, profile_tokens, intent)
            if score >= self.min_score:
                scored_entries.append((score, entry))

        selected = self._select_diverse_entries(scored_entries)
        return [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "score": score,
                "category": entry.category,
                "tags": entry.tags,
                "examples": entry.examples,
            }
            for score, entry in selected
        ]

    def _load_entries(self) -> list[KnowledgeEntry]:
        if not self.kb_path.exists():
            return []

        payload = json.loads(self.kb_path.read_text(encoding="utf-8"))
        entries: list[KnowledgeEntry] = []
        for raw_entry in payload:
            entries.append(
                KnowledgeEntry(
                    id=str(raw_entry["id"]),
                    title=str(raw_entry["title"]),
                    content=str(raw_entry["content"]),
                    intents=[str(item) for item in raw_entry.get("intents", [])],
                    tags=[str(item) for item in raw_entry.get("tags", [])],
                    category=str(raw_entry.get("category", "")),
                    profile_tags=[str(item) for item in raw_entry.get("profile_tags", [])],
                    examples=[str(item) for item in raw_entry.get("examples", [])],
                )
            )
        return entries

    def _build_profile_hint_tokens(self, profile: UserProfile, intent: str) -> set[str]:
        tokens: set[str] = set()

        scalar_values: tuple[str | None, ...]
        list_values: tuple[list[str], ...]

        if intent == "request_meal_guidance":
            scalar_values = (
                profile.goal,
                profile.budget_level,
                profile.cook_time_preference,
            )
            list_values = (
                profile.diet_preferences,
                profile.allergies,
                profile.preferred_foods,
                profile.disliked_foods,
            )
        elif intent == "request_workout_plan":
            scalar_values = (
                profile.goal,
                profile.train_location,
                profile.experience_level,
            )
            list_values = (
                profile.injuries,
            )
        else:
            scalar_values = (
                profile.goal,
                profile.train_location,
                profile.experience_level,
                profile.budget_level,
                profile.cook_time_preference,
            )
            list_values = (
                profile.injuries,
                profile.diet_preferences,
                profile.allergies,
                profile.preferred_foods,
                profile.disliked_foods,
            )

        for value in scalar_values:
            if value:
                tokens.update(self._tokenize(str(value)))

        for items in list_values:
            for item in items:
                tokens.update(self._tokenize(item))

        if profile.goal_detail:
            tokens.update(self._tokenize(profile.goal_detail))

        if profile.goal == "muscle_gain":
            tokens.update({"tang_co", "muscle_gain", "protein", "calories"})
        elif profile.goal == "fat_loss":
            tokens.update({"giam_mo", "fat_loss", "it_calorie", "no_lau"})

        if intent != "request_workout_plan" and profile.budget_level == "low":
            tokens.update({"budget_low", "tiet_kiem", "gia_re", "chi_phi"})
        elif intent != "request_workout_plan" and profile.budget_level == "high":
            tokens.update({"budget_high", "chat_luong_cao", "da_dang"})

        if intent != "request_workout_plan" and profile.cook_time_preference == "quick":
            tokens.update({"quick", "nhanh", "prep_nhanh", "it_thoi_gian"})

        if intent != "request_meal_guidance" and profile.train_location == "home":
            tokens.update({"home", "o_nha", "bodyweight", "dumbbell"})
        elif intent != "request_meal_guidance" and profile.train_location == "gym":
            tokens.update({"gym", "may_tap", "barbell", "cable"})

        normalized_preferences = {normalize_text(item) for item in profile.diet_preferences}
        normalized_allergies = {normalize_text(item) for item in profile.allergies}
        if intent != "request_workout_plan" and {"vegetarian", "an chay", "vegan"} & normalized_preferences:
            tokens.update({"vegetarian", "an_chay", "plant_protein", "dau_hu", "dau_nanh"})
        if intent != "request_workout_plan" and {"milk", "sua", "dairy", "lactose"} & normalized_allergies:
            tokens.update({"dairy_free", "khong_sua", "lactose_free", "sua_dau_nanh"})

        normalized_injuries = {normalize_text(item) for item in profile.injuries}
        if intent != "request_meal_guidance" and {"knee", "goi", "dau goi"} & normalized_injuries:
            tokens.update({"knee", "dau_goi", "rom", "hip_hinge"})
        if intent != "request_meal_guidance" and {"shoulder", "vai", "dau vai"} & normalized_injuries:
            tokens.update({"shoulder", "vai", "face_pull", "upper_body"})

        return tokens

    def _allowed_category_prefixes(self, intent: str) -> tuple[str, ...] | None:
        if intent == "request_meal_guidance":
            return ("meal_",)
        if intent == "request_workout_plan":
            return ("workout_", "recovery_")
        return None

    def _is_entry_allowed_for_intent(
        self,
        entry: KnowledgeEntry,
        allowed_category_prefixes: tuple[str, ...] | None,
    ) -> bool:
        if allowed_category_prefixes is None:
            return True
        return bool(entry.category) and entry.category.startswith(allowed_category_prefixes)

    def _score_entry(
        self,
        entry: KnowledgeEntry,
        message_tokens: set[str],
        profile_tokens: set[str],
        intent: str,
    ) -> int:
        title_tokens = self._tokenize(entry.title)
        content_tokens = self._tokenize(entry.content)
        tag_tokens = self._flatten_tokens(entry.tags)
        entry_profile_tokens = self._flatten_tokens(entry.profile_tags)
        example_tokens = self._flatten_tokens(entry.examples)
        category_tokens = self._tokenize(entry.category)

        message_overlap = (
            len(message_tokens & tag_tokens) * 4
            + len(message_tokens & entry_profile_tokens) * 5
            + len(message_tokens & example_tokens) * 3
            + len(message_tokens & title_tokens) * 3
            + len(message_tokens & content_tokens) * 2
            + len(message_tokens & category_tokens) * 2
        )
        profile_overlap = (
            len(profile_tokens & tag_tokens) * 2
            + len(profile_tokens & entry_profile_tokens) * 3
            + len(profile_tokens & example_tokens)
            + len(profile_tokens & title_tokens)
            + len(profile_tokens & content_tokens)
            + len(profile_tokens & category_tokens)
        )

        if message_overlap == 0 and profile_overlap == 0:
            return 0

        score = message_overlap + profile_overlap
        combined_tokens = message_tokens | profile_tokens
        category_signal_tokens = CATEGORY_SIGNAL_TOKENS.get(entry.category, set())
        category_signal_matches = combined_tokens & category_signal_tokens
        score += len(category_signal_matches) * 2
        if category_signal_matches:
            score += CATEGORY_SIGNAL_BONUS.get(entry.category, 0)
        if intent in entry.intents:
            score += 3 if message_overlap > 0 else 1
        if intent == "request_meal_guidance":
            if entry.category.startswith("meal_"):
                score += 2
        if intent == "request_workout_plan":
            if entry.category.startswith(("workout_", "recovery_")):
                score += 2
        if intent == "general_fitness_qa" and message_overlap > 0:
            score += 1
        return score

    def _select_diverse_entries(
        self,
        scored_entries: list[tuple[int, KnowledgeEntry]],
    ) -> list[tuple[int, KnowledgeEntry]]:
        scored_entries.sort(
            key=lambda item: (
                item[0],
                len(item[1].examples),
                len(item[1].profile_tags),
                len(item[1].tags),
            ),
            reverse=True,
        )

        selected: list[tuple[int, KnowledgeEntry]] = []
        used_categories: set[str] = set()

        for score, entry in scored_entries:
            if entry.category and entry.category in used_categories:
                continue
            selected.append((score, entry))
            if entry.category:
                used_categories.add(entry.category)
            if len(selected) >= self.top_k:
                return selected

        for score, entry in scored_entries:
            if any(existing.id == entry.id for _, existing in selected):
                continue
            selected.append((score, entry))
            if len(selected) >= self.top_k:
                break

        return selected

    def _flatten_tokens(self, values: list[str]) -> set[str]:
        flattened: set[str] = set()
        for value in values:
            flattened.update(self._tokenize(value))
        return flattened

    def _expand_tokens(self, tokens: set[str]) -> set[str]:
        expanded = set(tokens)
        pending = list(tokens)
        while pending:
            token = pending.pop()
            for related in TOKEN_EXPANSIONS.get(token, set()):
                if related not in expanded:
                    expanded.add(related)
                    pending.append(related)
        return expanded

    def _tokenize(self, value: str) -> set[str]:
        normalized = normalize_text(value)
        ordered_tokens = [token for token in TOKEN_PATTERN.findall(normalized) if token not in STOPWORDS]
        tokens = set(ordered_tokens)
        if len(ordered_tokens) >= 2:
            tokens.update(
                f"{ordered_tokens[index]}_{ordered_tokens[index + 1]}"
                for index in range(len(ordered_tokens) - 1)
            )
        if len(ordered_tokens) >= 2:
            tokens.add("_".join(ordered_tokens))
        return tokens
