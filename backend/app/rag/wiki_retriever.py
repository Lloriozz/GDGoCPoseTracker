from __future__ import annotations

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
PAGE_TYPE_PATTERN = re.compile(r"^\*\*Page type\*\*:\s*([a-zA-Z\-]+)\s*$", re.MULTILINE)
SUMMARY_PATTERN = re.compile(r"^\*\*Summary\*\*:\s*(.+?)\s*$", re.MULTILINE)
TITLE_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
SECTION_KEYWORDS = {
    "meal": {
        "an",
        "bua",
        "mon",
        "thuc_don",
        "substitution",
        "thay_mon",
        "thay_the",
        "pho",
        "bun",
        "com",
        "do_viet",
        "mon_viet",
    },
    "nutrition": {
        "dinh_duong",
        "protein",
        "carb",
        "fat",
        "chat_xo",
        "calorie_deficit",
        "giam_mo",
        "fat_loss",
        "tang_co",
        "muscle_gain",
        "leucine",
        "omega_3",
    },
    "fasting": {
        "fasting",
        "nhin_an",
        "intermittent",
        "intermittent_fasting",
        "if",
        "an_theo_gio",
    },
    "recovery": {
        "recovery",
        "hoi_phuc",
        "sau_tap",
        "post_workout",
        "hydration",
        "dien_giai",
        "ngu",
        "mat_nuoc",
        "deload",
        "met_moi",
    },
    "workout": {
        "workout",
        "tap",
        "lich_tap",
        "progressive_overload",
        "overload",
        "chan_thuong",
        "nen",
        "tranh",
        "dau_goi",
    },
}
PAGE_TYPE_BONUS = {
    "concept": 10,
    "comparison": 7,
    "entity": 6,
    "index": 2,
    "source-summary": -3,
}


@dataclass(slots=True)
class WikiPage:
    id: str
    path: str
    title: str
    summary: str
    content: str
    page_type: str
    section: str
    sources: list[str] = field(default_factory=list)


class WikiKnowledgeRetriever:
    def __init__(
        self,
        wiki_path: str | None = None,
        top_k: int | None = None,
        min_score: int | None = None,
    ) -> None:
        self.wiki_path = Path(wiki_path or settings.wiki_path)
        self.top_k = top_k or settings.wiki_top_k
        self.min_score = min_score or settings.wiki_min_score
        self._pages = self._load_pages()
        self._snapshot = self._build_snapshot()

    def retrieve(
        self,
        message: str,
        intent: str,
        profile: UserProfile,
        allowed_sections: set[str] | None = None,
    ) -> list[dict[str, object]]:
        if not settings.wiki_enabled:
            return []
        self._refresh_if_needed()
        if not self._pages:
            return []

        if allowed_sections is None:
            allowed_sections = self._allowed_sections(message=message, intent=intent)
        if not allowed_sections:
            return []

        message_tokens = self._expand_tokens(self._tokenize(message))
        profile_tokens = self._expand_tokens(self._build_profile_hint_tokens(profile, intent))
        if not message_tokens and not profile_tokens:
            return []

        scored_pages: list[tuple[int, WikiPage]] = []
        for page in self._pages:
            if page.section not in allowed_sections and page.section != "root":
                continue
            score = self._score_page(
                page=page,
                message_tokens=message_tokens,
                profile_tokens=profile_tokens,
                allowed_sections=allowed_sections,
            )
            if score >= self.min_score:
                scored_pages.append((score, page))

        return [
            {
                "id": page.id,
                "title": page.title,
                "content": page.content,
                "score": score,
                "category": f"wiki_{page.section}_{page.page_type}",
                "section": page.section,
                "page_type": page.page_type,
                "path": page.path,
                "source": "wiki",
                "examples": [],
            }
            for score, page in self._select_pages(scored_pages)
        ]

    def _refresh_if_needed(self) -> None:
        snapshot = self._build_snapshot()
        if snapshot != self._snapshot:
            self._pages = self._load_pages()
            self._snapshot = snapshot

    def _load_pages(self) -> list[WikiPage]:
        if not self.wiki_path.exists():
            return []

        pages: list[WikiPage] = []
        for path in sorted(self.wiki_path.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(self.wiki_path)
            relative_path = relative.as_posix()
            stem_path = relative.with_suffix("").as_posix()
            section = relative.parts[0] if len(relative.parts) > 1 else "root"
            title = self._extract_first_match(TITLE_PATTERN, text) or path.stem.replace("-", " ").title()
            summary = self._extract_first_match(SUMMARY_PATTERN, text)
            page_type = (self._extract_first_match(PAGE_TYPE_PATTERN, text) or "concept").strip().lower()
            key_points = self._extract_section(text, "Key Points")
            practical_notes = self._extract_section(text, "Practical Notes")
            content = "\n".join(part for part in [summary, key_points, practical_notes] if part).strip()
            sources = self._extract_sources(text)
            pages.append(
                WikiPage(
                    id=stem_path,
                    path=relative_path,
                    title=title,
                    summary=summary,
                    content=content,
                    page_type=page_type,
                    section=section,
                    sources=sources,
                )
            )
        return pages

    def _build_snapshot(self) -> tuple[tuple[str, int], ...]:
        if not self.wiki_path.exists():
            return ()
        files: list[tuple[str, int]] = []
        for path in sorted(self.wiki_path.rglob("*.md")):
            stat = path.stat()
            files.append((path.relative_to(self.wiki_path).as_posix(), stat.st_mtime_ns))
        return tuple(files)

    def _allowed_sections(self, message: str, intent: str) -> set[str]:
        if intent == "request_meal_guidance":
            return {"meal", "nutrition", "fasting", "recovery"}
        if intent == "request_workout_plan":
            return {"workout", "recovery"}
        if intent != "general_fitness_qa":
            return set()

        tokens = self._expand_tokens(self._tokenize(message))
        matched_sections = {
            section
            for section, keywords in SECTION_KEYWORDS.items()
            if tokens & keywords
        }
        if matched_sections:
            return matched_sections
        return set()

    def _score_page(
        self,
        page: WikiPage,
        message_tokens: set[str],
        profile_tokens: set[str],
        allowed_sections: set[str],
    ) -> int:
        title_tokens = self._tokenize(page.title)
        summary_tokens = self._tokenize(page.summary)
        content_tokens = self._tokenize(page.content)
        section_tokens = self._tokenize(page.section)
        source_tokens = self._flatten_tokens(page.sources)

        combined_tokens = message_tokens | profile_tokens
        overlap_score = (
            len(message_tokens & title_tokens) * 6
            + len(message_tokens & summary_tokens) * 5
            + len(message_tokens & content_tokens) * 3
            + len(profile_tokens & title_tokens) * 2
            + len(profile_tokens & summary_tokens) * 2
            + len(profile_tokens & content_tokens)
            + len(combined_tokens & section_tokens) * 2
            + len(message_tokens & source_tokens)
        )
        if overlap_score == 0:
            return 0

        score = overlap_score + PAGE_TYPE_BONUS.get(page.page_type, 0)
        if page.section in allowed_sections:
            score += 3
        if page.section == "root":
            score -= 1
        if page.page_type == "index" and page.section != "root":
            score -= 1
        return score

    def _select_pages(self, scored_pages: list[tuple[int, WikiPage]]) -> list[tuple[int, WikiPage]]:
        scored_pages.sort(
            key=lambda item: (
                item[0],
                PAGE_TYPE_BONUS.get(item[1].page_type, 0),
                len(item[1].sources),
            ),
            reverse=True,
        )

        selected: list[tuple[int, WikiPage]] = []
        used_sections: set[str] = set()
        used_source_summaries = 0

        for score, page in scored_pages:
            if page.page_type == "source-summary":
                if used_source_summaries >= 1:
                    continue
                if page.section in used_sections:
                    continue

            if page.page_type in {"concept", "comparison", "entity"} and page.section in used_sections:
                continue

            selected.append((score, page))
            if page.section != "root":
                used_sections.add(page.section)
            if page.page_type == "source-summary":
                used_source_summaries += 1
            if len(selected) >= self.top_k:
                return selected

        return selected

    def _build_profile_hint_tokens(self, profile: UserProfile, intent: str) -> set[str]:
        tokens: set[str] = set()
        if profile.goal:
            tokens.update(self._tokenize(profile.goal))
        if profile.goal_detail:
            tokens.update(self._tokenize(profile.goal_detail))
        if intent == "request_meal_guidance":
            tokens.update(self._flatten_tokens(profile.preferred_foods))
            tokens.update(self._flatten_tokens(profile.diet_preferences))
            tokens.update(self._flatten_tokens(profile.allergies))
        if intent == "request_workout_plan":
            tokens.update(self._flatten_tokens(profile.injuries))
            if profile.train_location:
                tokens.update(self._tokenize(profile.train_location))

        normalized_goal = normalize_text(profile.goal or "")
        if normalized_goal == "muscle_gain":
            tokens.update({"tang_co", "muscle_gain", "protein"})
        elif normalized_goal == "fat_loss":
            tokens.update({"giam_mo", "fat_loss", "calorie_deficit"})
        return tokens

    def _extract_section(self, text: str, heading: str) -> str:
        pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            return ""
        tail = text[match.end():]
        next_heading = re.search(r"^##\s+", tail, re.MULTILINE)
        section_text = tail[: next_heading.start()] if next_heading else tail
        lines = [line.strip("- ").strip() for line in section_text.splitlines() if line.strip()]
        return " ".join(lines).strip()

    def _extract_sources(self, text: str) -> list[str]:
        lines = text.splitlines()
        start_index: int | None = None
        for index, line in enumerate(lines):
            if line.strip() == "**Sources**:":
                start_index = index + 1
                break
        if start_index is None:
            return []

        sources: list[str] = []
        for line in lines[start_index:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("**Last updated**:") or stripped.startswith("---"):
                break
            if stripped.startswith("- "):
                sources.append(stripped[2:].strip())
        return sources

    def _extract_first_match(self, pattern: re.Pattern[str], text: str) -> str:
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    def _flatten_tokens(self, values: list[str]) -> set[str]:
        flattened: set[str] = set()
        for value in values:
            flattened.update(self._tokenize(value))
        return flattened

    def _expand_tokens(self, tokens: set[str]) -> set[str]:
        expansions = {
            "tang": {"tang_co", "muscle_gain", "protein"},
            "tang_co": {"muscle_gain", "protein"},
            "muscle_gain": {"tang_co", "protein"},
            "giam_mo": {"fat_loss", "calorie_deficit"},
            "fat_loss": {"giam_mo", "calorie_deficit"},
            "nhin_an": {"fasting", "intermittent_fasting"},
            "hoi_phuc": {"recovery", "post_workout"},
            "pho": {"mon_viet", "meal"},
            "bun": {"mon_viet", "meal"},
            "com": {"mon_viet", "meal"},
        }
        expanded = set(tokens)
        pending = list(tokens)
        while pending:
            token = pending.pop()
            for related in expansions.get(token, set()):
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
            tokens.add("_".join(ordered_tokens))
        return tokens
