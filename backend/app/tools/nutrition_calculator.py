from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text_utils import normalize_text
from app.tools.nutrition_catalog import NutritionCatalog, load_nutrition_catalog


PRECISE_UNITS = {"g", "gram", "gr", "kg", "ml", "l", "qua", "trai", "cai"}
ESTIMATE_UNITS = {"bat", "chen", "to", "phan", "muong", "thia"}
ALL_UNITS = PRECISE_UNITS | ESTIMATE_UNITS
UNIT_ALIASES = {
    "g": "g",
    "gram": "g",
    "gr": "g",
    "kg": "kg",
    "ml": "ml",
    "l": "l",
    "qua": "qua",
    "trai": "qua",
    "cai": "qua",
    "bat": "bat",
    "chen": "chen",
    "to": "to",
    "phan": "phan",
    "muong": "muong",
    "thia": "muong",
}
NUTRITION_KEYWORDS = {
    "calo",
    "calories",
    "kcal",
    "protein",
    "carb",
    "fat",
    "macro",
    "nguyen lieu",
    "dinh duong",
    "uoc luong",
    "uoc tinh",
}
PROFILE_REQUEST_KEYWORDS = {
    "tdee",
    "lich tap",
    "workout",
    "giao an",
    "split",
    "thuc don",
    "meal plan",
    "tuoi",
    "cao",
    "nang",
    "muc tieu",
    "tang co",
    "giam mo",
    "gym",
    "buoi moi tuan",
}
QUANTITY_PATTERN = re.compile(
    r"(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|gram|gr|g|ml|l|qua|trai|cai|bat|chen|to|phan|muong|thia)\b"
)
SEGMENT_PATTERN = re.compile(
    r"^(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|gram|gr|g|ml|l|qua|trai|cai|bat|chen|to|phan|muong|thia)\b\s*(?P<name>.+)$"
)


@dataclass(slots=True)
class ParsedNutritionItem:
    quantity: float
    unit: str
    name: str
    source_text: str

    @property
    def is_estimate_unit(self) -> bool:
        return self.unit in ESTIMATE_UNITS


def looks_like_nutrition_request(message: str) -> bool:
    normalized = normalize_text(message)
    quantity_matches = list(QUANTITY_PATTERN.finditer(normalized))
    if len(quantity_matches) >= 2:
        return True
    if len(quantity_matches) != 1:
        return False
    if any(keyword in normalized for keyword in PROFILE_REQUEST_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in NUTRITION_KEYWORDS)


def build_nutrition_reply(tool_results: dict[str, object]) -> str:
    clarification = tool_results.get("clarification_request", {})
    if isinstance(clarification, dict) and clarification.get("question"):
        return str(clarification["question"])

    estimate = tool_results.get("nutrition_estimate", {})
    if not isinstance(estimate, dict):
        return "Minh chua tinh duoc dinh duong cho du lieu hien tai."

    items = estimate.get("items", [])
    totals = estimate.get("totals", {})
    assumptions = estimate.get("assumptions", [])
    unmatched_items = estimate.get("unmatched_items", [])
    mode = str(estimate.get("mode", "precise"))
    llm_fallback = estimate.get("llm_fallback", {})
    llm_fallback_reply = ""
    if isinstance(llm_fallback, dict):
        llm_fallback_reply = str(llm_fallback.get("reply", "")).strip()

    if not items and unmatched_items:
        if llm_fallback_reply:
            return llm_fallback_reply
        unmatched_text = ", ".join(str(item) for item in unmatched_items)
        return (
            "Minh chua nhan ra mot so mon/nguyen lieu trong phan ban nhap: "
            f"{unmatched_text}. Ban co the nhap lai ro hon theo dang `150g thit bo song` "
            "hoac `1 to pho bo`."
        )

    opening = (
        "Minh da uoc luong dinh duong theo khau phan pho bien cho phan ban nhap:"
        if mode == "estimated"
        else "Minh da tinh dinh duong cho phan ban nhap:"
    )
    lines = [opening]

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        prefix = f"- {item.get('display_name', 'Mon')}"
        display_amount = str(item.get("display_amount", "")).strip()
        if display_amount:
            prefix += f" ({display_amount})"
        lines.append(
            (
                f"{prefix}: {_format_number(item.get('calories', 0))} kcal | "
                f"{_format_number(item.get('protein_g', 0))}g protein | "
                f"{_format_number(item.get('carb_g', 0))}g carb | "
                f"{_format_number(item.get('fat_g', 0))}g fat"
            )
        )

    if isinstance(totals, dict):
        lines.append(
            (
                "Tong: "
                f"{_format_number(totals.get('calories', 0))} kcal | "
                f"{_format_number(totals.get('protein_g', 0))}g protein | "
                f"{_format_number(totals.get('carb_g', 0))}g carb | "
                f"{_format_number(totals.get('fat_g', 0))}g fat"
            )
        )

    if unmatched_items and llm_fallback_reply:
        lines.append("Cac muc chua co trong catalog, minh uoc luong so bo nhu sau:")
        lines.append(llm_fallback_reply)
    elif unmatched_items:
        unmatched_text = ", ".join(str(item) for item in unmatched_items)
        lines.append(
            "Minh chua cong duoc cac muc nay vi con mo ho hoac chua co alias phu hop: "
            f"{unmatched_text}. Ban co the nhap lai ro hon neu muon cong tiep."
        )

    if assumptions:
        lines.append("Luu y: " + "; ".join(str(item) for item in assumptions))

    if mode == "estimated":
        lines.append(
            "Day la uoc luong theo khau phan pho bien, nen co the lech nhe so voi khau phan thuc te cua ban."
        )

    return "\n".join(lines)


class NutritionCalculator:
    def __init__(self, catalog: NutritionCatalog | None = None) -> None:
        self.catalog = catalog or load_nutrition_catalog()

    def parse_message(self, message: str) -> list[ParsedNutritionItem]:
        normalized = self._normalize_message_for_parse(message)
        segments = [segment.strip() for segment in re.split(r"[,;\n]+", normalized) if segment.strip()]
        parsed_items: list[ParsedNutritionItem] = []

        for segment in segments:
            first_digit_index = next((index for index, char in enumerate(segment) if char.isdigit()), -1)
            if first_digit_index < 0:
                continue

            candidate = segment[first_digit_index:].strip()
            match = SEGMENT_PATTERN.match(candidate)
            if not match:
                continue

            quantity = float(match.group("qty").replace(",", "."))
            unit = UNIT_ALIASES.get(match.group("unit").strip(), match.group("unit").strip())
            if unit not in ALL_UNITS:
                continue

            name = self._clean_item_name(match.group("name"))
            if not name:
                continue

            parsed_items.append(
                ParsedNutritionItem(
                    quantity=quantity,
                    unit=unit,
                    name=name,
                    source_text=candidate,
                )
            )

        return parsed_items

    def build_estimate(self, message: str, mode: str | None = None) -> dict[str, object]:
        parsed_items = self.parse_message(message)
        explicit_estimate = self._contains_estimate_keyword(message)

        if not parsed_items:
            clarification = {
                "type": "nutrition_reformat",
                "question": (
                    "Minh chua doc duoc nguyen lieu va so luong du ro. Ban co the nhap theo dang "
                    "`200g uc ga, 100g gao song, 2 qua trung` hoac `1 bat com` neu muon minh uoc luong."
                ),
            }
            return {
                "reply": clarification["question"],
                "tool_results": {
                    "nutrition_estimate": {
                        "mode": "precise",
                        "items": [],
                        "totals": self._empty_totals(),
                        "assumptions": [],
                        "unmatched_items": [],
                        "needs_clarification": False,
                    },
                    "clarification_request": clarification,
                },
                "needs_clarification": False,
                "clarification_payload": None,
            }

        estimate_items = [item for item in parsed_items if item.is_estimate_unit]
        if estimate_items and mode is None and not explicit_estimate:
            item_labels = [item.source_text for item in estimate_items]
            question = (
                "Minh thay ban dang nhap theo khau phan pho bien nhu "
                f"{', '.join(f'`{label}`' for label in item_labels)}. "
                "Ban muon minh tinh theo gram/ml/qua hay cho minh uoc luong theo khau phan pho bien?"
            )
            return {
                "reply": question,
                "tool_results": {
                    "nutrition_estimate": {
                        "mode": "precise",
                        "items": [],
                        "totals": self._empty_totals(),
                        "assumptions": [],
                        "unmatched_items": [],
                        "needs_clarification": True,
                    },
                    "clarification_request": {
                        "type": "nutrition_mode_selection",
                        "question": question,
                        "items": item_labels,
                        "options": ["gram", "estimate"],
                    },
                },
                "needs_clarification": True,
                "clarification_payload": {
                    "type": "nutrition_mode_selection",
                    "estimate_items": item_labels,
                },
            }

        if estimate_items and mode == "precise":
            question = (
                "Ok, ban nhap lai giup minh theo gram/ml/qua de minh tinh chinh xac hon nhe. "
                "Vi du: `160g com trang, 150g thit bo`."
            )
            return {
                "reply": question,
                "tool_results": {
                    "nutrition_estimate": {
                        "mode": "precise",
                        "items": [],
                        "totals": self._empty_totals(),
                        "assumptions": [],
                        "unmatched_items": [],
                        "needs_clarification": False,
                    },
                    "clarification_request": {
                        "type": "nutrition_precise_reentry",
                        "question": question,
                    },
                },
                "needs_clarification": False,
                "clarification_payload": None,
            }

        result_mode = "estimated" if estimate_items else "precise"
        return self._calculate(parsed_items, mode=result_mode)

    def handle_pending_clarification(
        self,
        pending_payload: dict[str, object],
        message: str,
    ) -> dict[str, object] | None:
        if str(pending_payload.get("type", "")) != "nutrition_mode_selection":
            return None

        original_message = str(pending_payload.get("original_message", "")).strip()
        if not original_message:
            return None

        normalized = normalize_text(message)
        if self._contains_estimate_selection(normalized):
            return self.build_estimate(original_message, mode="estimated")
        if self._contains_gram_selection(normalized):
            return self.build_estimate(original_message, mode="precise")
        return None

    def should_consume_pending_clarification(self, message: str) -> bool:
        normalized = normalize_text(message)
        return self._contains_estimate_selection(normalized) or self._contains_gram_selection(normalized)

    def _calculate(self, parsed_items: list[ParsedNutritionItem], mode: str) -> dict[str, object]:
        items: list[dict[str, object]] = []
        assumptions: list[str] = []
        unmatched_items: list[str] = []
        unmatched_inputs: list[str] = []
        totals = self._empty_totals()

        for parsed_item in parsed_items:
            food, _ = self.catalog.match_food(parsed_item.name)
            if not food:
                unmatched_items.append(parsed_item.name)
                unmatched_inputs.append(parsed_item.source_text)
                continue

            if parsed_item.is_estimate_unit:
                item_result = self._calculate_estimated_item(parsed_item, food)
            else:
                item_result = self._calculate_precise_item(parsed_item, food)

            if item_result is None:
                unmatched_items.append(parsed_item.name)
                unmatched_inputs.append(parsed_item.source_text)
                continue

            items.append(item_result)
            totals["calories"] += float(item_result["calories"])
            totals["protein_g"] += float(item_result["protein_g"])
            totals["carb_g"] += float(item_result["carb_g"])
            totals["fat_g"] += float(item_result["fat_g"])

            if food.get("generic"):
                assumptions.append(
                    f"`{parsed_item.name}` duoc map sang nhom uoc luong `{food.get('display_name', food.get('id'))}`."
                )
            if item_result.get("assumption"):
                assumptions.append(str(item_result["assumption"]))

        tool_results = {
            "nutrition_estimate": {
                "mode": mode,
                "items": items,
                "totals": self._round_totals(totals),
                "assumptions": self._dedupe_preserve_order(assumptions),
                "unmatched_items": self._dedupe_preserve_order(unmatched_items),
                "unmatched_inputs": self._dedupe_preserve_order(unmatched_inputs),
                "needs_clarification": False,
            }
        }
        return {
            "reply": build_nutrition_reply(tool_results),
            "tool_results": tool_results,
            "needs_clarification": False,
            "clarification_payload": None,
        }

    def _calculate_precise_item(
        self,
        parsed_item: ParsedNutritionItem,
        food: dict[str, object],
    ) -> dict[str, object] | None:
        grams_used, assumption = self._convert_to_grams(parsed_item, food)
        if grams_used is None:
            return None

        nutrients = self._nutrients_from_grams(food, grams_used)
        return {
            "display_name": str(food.get("display_name", parsed_item.name)),
            "canonical_id": str(food.get("id", "")),
            "display_amount": f"{self._format_quantity(parsed_item.quantity)} {parsed_item.unit}",
            "grams_used": round(grams_used, 1),
            "estimated": False,
            "assumption": assumption,
            **nutrients,
        }

    def _calculate_estimated_item(
        self,
        parsed_item: ParsedNutritionItem,
        food: dict[str, object],
    ) -> dict[str, object] | None:
        template = self.catalog.get_portion_template(str(food.get("id")), parsed_item.unit)
        if template is None:
            return None

        multiplier = parsed_item.quantity
        grams_used = template.get("grams")
        if grams_used is not None:
            grams_value = float(grams_used) * multiplier
            nutrients = self._nutrients_from_grams(food, grams_value)
        else:
            grams_value = None
            nutrients = {
                "calories": round(float(template.get("calories", 0)) * multiplier, 1),
                "protein_g": round(float(template.get("protein_g", 0)) * multiplier, 1),
                "carb_g": round(float(template.get("carb_g", 0)) * multiplier, 1),
                "fat_g": round(float(template.get("fat_g", 0)) * multiplier, 1),
            }

        display_amount = (
            str(template.get("display_label", "")).strip()
            if multiplier == 1 and str(template.get("display_label", "")).strip()
            else f"{self._format_quantity(parsed_item.quantity)} {parsed_item.unit}"
        )
        return {
            "display_name": str(food.get("display_name", parsed_item.name)),
            "canonical_id": str(food.get("id", "")),
            "display_amount": display_amount,
            "grams_used": round(grams_value, 1) if grams_value is not None else None,
            "estimated": True,
            "assumption": template.get("assumption"),
            **nutrients,
        }

    def _convert_to_grams(
        self,
        parsed_item: ParsedNutritionItem,
        food: dict[str, object],
    ) -> tuple[float | None, str | None]:
        food_id = str(food.get("id"))

        if parsed_item.unit == "g":
            return parsed_item.quantity, None
        if parsed_item.unit == "kg":
            return parsed_item.quantity * 1000, "Dung quy doi 1 kg = 1000 g."
        if parsed_item.unit == "l":
            conversion = self.catalog.get_unit_conversion(food_id, "ml")
            if conversion is not None:
                return parsed_item.quantity * 1000 * conversion, "Dung quy doi 1 lit = 1000 ml."
            return None, None
        if parsed_item.unit == "ml":
            conversion = self.catalog.get_unit_conversion(food_id, "ml")
            if conversion is not None:
                return parsed_item.quantity * conversion, None
            density = food.get("density_g_per_ml")
            if density is not None:
                return parsed_item.quantity * float(density), "Dung mat do mac dinh theo ml cho nguyen lieu dang long."
            return None, None
        if parsed_item.unit == "qua":
            conversion = self.catalog.get_unit_conversion(food_id, "qua")
            if conversion is not None:
                return parsed_item.quantity * conversion, None
            return None, None
        return None, None

    def _nutrients_from_grams(self, food: dict[str, object], grams_used: float) -> dict[str, float]:
        per_100g = food.get("per_100g", {})
        if not isinstance(per_100g, dict):
            per_100g = {}
        factor = grams_used / 100 if grams_used else 0
        return {
            "calories": round(float(per_100g.get("calories", 0)) * factor, 1),
            "protein_g": round(float(per_100g.get("protein_g", 0)) * factor, 1),
            "carb_g": round(float(per_100g.get("carb_g", 0)) * factor, 1),
            "fat_g": round(float(per_100g.get("fat_g", 0)) * factor, 1),
        }

    def _normalize_message_for_parse(self, message: str) -> str:
        normalized = normalize_text(message)
        normalized = normalized.replace("&", ",")
        normalized = re.sub(r"\s+va\s+", ", ", normalized)
        normalized = re.sub(r"\s*\+\s*", ", ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _clean_item_name(self, value: str) -> str:
        cleaned = value.strip(" .!?")
        for marker in [
            "bao nhieu calo",
            "bao nhieu kcal",
            "bao nhieu protein",
            "bao nhieu macro",
            "bao nhieu",
            "giup minh",
            "giup toi",
            "cho toi",
            "nhe",
            "duoc khong",
        ]:
            if marker in cleaned:
                cleaned = cleaned.split(marker, maxsplit=1)[0].strip(" .!?")
        return cleaned

    def _contains_estimate_keyword(self, message: str) -> bool:
        normalized = normalize_text(message)
        return any(
            keyword in normalized
            for keyword in ["uoc luong", "uoc tinh", "khau phan pho bien", "theo khau phan", "estimate"]
        )

    def _contains_estimate_selection(self, normalized_message: str) -> bool:
        return any(
            keyword in normalized_message
            for keyword in ["uoc luong", "uoc tinh", "khau phan pho bien", "estimate"]
        )

    def _contains_gram_selection(self, normalized_message: str) -> bool:
        return any(
            keyword in normalized_message
            for keyword in ["theo gram", "nhap theo gram", "gram", "ml", "qua", "chinh xac hon"]
        )

    def _format_quantity(self, value: float) -> str:
        return _format_number(value)

    def _empty_totals(self) -> dict[str, float]:
        return {
            "calories": 0.0,
            "protein_g": 0.0,
            "carb_g": 0.0,
            "fat_g": 0.0,
        }

    def _round_totals(self, totals: dict[str, float]) -> dict[str, float]:
        return {key: round(value, 1) for key, value in totals.items()}

    def _dedupe_preserve_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered


def _format_number(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}".rstrip("0").rstrip(".")
