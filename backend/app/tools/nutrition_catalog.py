from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.core.text_utils import normalize_text


@dataclass(slots=True)
class NutritionCatalog:
    foods_by_id: dict[str, dict[str, object]]
    aliases: list[tuple[str, str]]
    unit_conversions: dict[tuple[str, str], float]
    portion_templates: dict[tuple[str, str], dict[str, object]]

    def match_food(self, name: str) -> tuple[dict[str, object] | None, str | None]:
        normalized_name = normalize_text(name).strip()
        if not normalized_name:
            return None, None

        for alias, food_id in self.aliases:
            if normalized_name == alias:
                return self.foods_by_id.get(food_id), alias

        for alias, food_id in self.aliases:
            if len(alias) < 4:
                continue
            if alias in normalized_name:
                return self.foods_by_id.get(food_id), alias

        return None, None

    def get_unit_conversion(self, food_id: str, unit: str) -> float | None:
        return self.unit_conversions.get((food_id, unit))

    def get_portion_template(self, food_id: str, unit: str) -> dict[str, object] | None:
        return self.portion_templates.get((food_id, unit))


@lru_cache(maxsize=1)
def load_nutrition_catalog(path: str | None = None) -> NutritionCatalog:
    catalog_path = Path(path or settings.nutrition_catalog_path)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))

    foods_by_id = {
        str(food["id"]): dict(food)
        for food in payload.get("foods", [])
    }
    aliases = sorted(
        (
            (normalize_text(str(item["alias"])).strip(), str(item["food_id"]))
            for item in payload.get("aliases", [])
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    unit_conversions = {
        (str(item["food_id"]), normalize_text(str(item["unit"])).strip()): float(item["grams"])
        for item in payload.get("unit_conversions", [])
    }
    portion_templates = {
        (str(item["food_id"]), normalize_text(str(item["unit"])).strip()): dict(item)
        for item in payload.get("portion_templates", [])
    }
    return NutritionCatalog(
        foods_by_id=foods_by_id,
        aliases=aliases,
        unit_conversions=unit_conversions,
        portion_templates=portion_templates,
    )
