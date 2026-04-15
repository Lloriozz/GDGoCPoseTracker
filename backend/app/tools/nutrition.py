from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text_utils import normalize_text
from app.tools.nutrition_catalog import NutritionCatalog, load_nutrition_catalog


PRECISE_UNITS = {"g", "gram", "gr", "kg", "ml", "l", "qua", "trai", "cai"}
ESTIMATE_UNITS = {"bat", "chen", "to", "phan", "muong", "thia"}
ALL_UNITS = PRECISE_UNITS | ESTIMATE_UNITS
UNIT_ALIASES = {
    "gram": "g",
    "gr": "g",
    "kg": "kg",
    "g": "g",
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
    quantity_matches = QUANTITY_PATTERN.findall(normalized)
    if len(quantity_matches) >= 2:
        return True
    if len(quantity_matches) == 1 and any(
        keyword in normalized
        for keyword in [
            "calo",
            "calories",
            "kcal",
            "protein",
            "carb",
            "fat",
            "macro",
            "nguyen lieu",
            "tinh",
            "uoc luong",
        ]
    ):
        return True
    if len(quantity_matches) == 1:
        unit = UNIT_ALIASES.get(quantity_matches[0][1], quantity_matches[0][1])
        return unit in ALL_UNITS
    return False


def build_nutrition_reply(tool_results: dict[str, object]) -> str:
    clarification = tool_results.get("clarification_request", {})
    if isinstance(clarification, dict) and clarification.get("question"):
        return str(clarification["question"])

    estimate = tool_results.get("nutrition_estimate", {})
    if not isinstance(estimate, dict):
        return "Mình chưa tính được dinh dưỡng cho dữ liệu hiện tại."

    items = estimate.get("items", [])
    totals = estimate.get("totals", {})
    assumptions = estimate.get("assumptions", [])
    unmatched_items = estimate.get("unmatched_items", [])
    mode = str(estimate.get("mode", "precise"))

    if not items and unmatched_items:
        unmatched_text = ", ".join(str(item) for item in unmatched_items)
        return (
            "Mình chưa nhận ra một số món/nguyên liệu trong phần bạn nhập: "
            f"{unmatched_text}. Bạn có thể nhập lại rõ hơn theo dạng như `150g thịt bò sống` hoặc `1 tô phở bò`."
        )

    opening = (
        "Mình đã ước lượng dinh dưỡng theo khẩu phần phổ biến cho phần bạn nhập:"
        if mode == "estimated"
        else "Mình đã tính dinh dưỡng cho phần bạn nhập:"
    )
    lines = [opening]
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        amount_label = str(item.get("display_amount", "")).strip()
        prefix = f"- {item.get('display_name', 'Món')}"
        if amount_label:
            prefix += f" ({amount_label})"
        lines.append(
            (
                f"{prefix}: {item.get('calories', 0)} kcal | "
                f"{item.get('protein_g', 0)}g protein | "
                f"{item.get('carb_g', 0)}g carb | "
                f"{item.get('fat_g', 0)}g fat"
            )
        )

    if isinstance(totals, dict):
        lines.append(
            (
                "Tổng: "
                f"{totals.get('calories', 0)} kcal | "
                f"{totals.get('protein_g', 0)}g protein | "
                f"{totals.get('carb_g', 0)}g carb | "
                f"{totals.get('fat_g', 0)}g fat"
            )
        )

    if unmatched_items:
        unmatched_text = ", ".join(str(item) for item in unmatched_items)
        lines.append(
            "Mình chưa cộng được các mục này vì còn mơ hồ hoặc chưa có alias phù hợp: "
            f"{unmatched_text}. Bạn có thể nhập lại rõ hơn nếu muốn cộng tiếp."
        )

    if assumptions:
        assumption_text = "; ".join(str(item) for item in assumptions)
        lines.append(f"Lưu ý: {assumption_text}")

    if mode == "estimated":
        lines.append("Đây là ước lượng theo khẩu phần phổ biến, nên có thể lệch nhẹ so với khẩu phần thực tế của bạn.")

    return "\n".join(lines)


class NutritionCalculator:
    def __init__(self, catalog: NutritionCatalog | None = None) -> None:
        self.catalog = catalog or load_nutrition_catalog()

    def parse_message(self, message: str) -> list[ParsedNutritionItem]:
        normalized = self._normalize_message_for_parse(message)
        segments = [
            segment.strip()
            for segment in re.split(r"[,;\n]+", normalized)
            if segment.strip()
        ]

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
            raw_unit = match.group("unit").strip()
            unit = UNIT_ALIASES.get(raw_unit, raw_unit)
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

    def build_estimate(
        self,
        message: str,
        mode: str | None = None,
    ) -> dict[str, object]:
        parsed_items = self.parse_message(message)
        explicit_estimate = self._contains_estimate_keyword(message)
        chosen_mode = mode or ("estimated" if explicit_estimate else "precise")

        if not parsed_items:
            clarification = {
                "type": "nutrition_reformat",
                "question": (
                    "Mình chưa đọc được nguyên liệu và số lượng đủ rõ. Bạn có thể nhập theo dạng "
                    "`200g ức gà, 100g gạo sống, 2 quả trứng` hoặc `1 bát cơm` nếu muốn mình ước lượng."
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
        if estimate_items and chosen_mode not in {"estimated", "precise"}:
            chosen_mode = "precise"

        if estimate_items and chosen_mode == "precise" and not explicit_estimate and mode is None:
            item_labels = [item.source_text for item in estimate_items]
            question = (
                "Mình thấy bạn đang nhập theo khẩu phần phổ biến như "
                f"{', '.join(f'`{label}`' for label in item_labels)}. "
                "Bạn muốn mình tính theo gram/ml/quả hay cho mình ước lượng theo khẩu phần phổ biến?"
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

        if estimate_items and chosen_mode == "precise" and mode == "precise":
            question = (
                "Ok, bạn nhập lại giúp mình theo gram/ml/quả để mình tính chính xác hơn nhé. "
                "Ví dụ: `160g cơm trắng, 1 tô phở bò ước lượng` hoặc `200g cơm chín, 150g thịt bò`."
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

        return self._calculate(parsed_items, mode="estimated" if estimate_items else "precise")

    def handle_pending_clarification(
        self,
        pending_payload: dict[str, object],
        message: str,
    ) -> dict[str, object] | None:
        pending_type = str(pending_payload.get("type", ""))
        if pending_type != "nutrition_mode_selection":
            return None

        normalized = normalize_text(message)
        if self._contains_estimate_selection(normalized):
            return self.build_estimate(str(pending_payload.get("original_message", "")), mode="estimated")
        if self._contains_gram_selection(normalized):
            return self.build_estimate(str(pending_payload.get("original_message", "")), mode="precise")
        return None

    def should_consume_pending_clarification(self, message: str) -> bool:
        normalized = normalize_text(message)
        return (
            self._contains_estimate_selection(normalized)
            or self._contains_gram_selection(normalized)
        )

    def _calculate(
        self,
        parsed_items: list[ParsedNutritionItem],
        mode: str,
    ) -> dict[str, object]:
        items: list[dict[str, object]] = []
        assumptions: list[str] = []
        unmatched_items: list[str] = []
        totals = self._empty_totals()

        for parsed_item in parsed_items:
            food, matched_alias = self.catalog.match_food(parsed_item.name)
            if not food:
                unmatched_items.append(parsed_item.name)
                continue

            if parsed_item.is_estimate_unit:
                item_result = self._calculate_estimated_item(parsed_item, food)
            else:
                item_result = self._calculate_precise_item(parsed_item, food)

            if item_result is None:
                unmatched_items.append(parsed_item.name)
                continue

            items.append(item_result)
            totals["calories"] += item_result["calories"]
            totals["protein_g"] += item_result["protein_g"]
            totals["carb_g"] += item_result["carb_g"]
            totals["fat_g"] += item_result["fat_g"]

            if matched_alias and food.get("generic"):
                assumptions.append(
                    f"`{parsed_item.name}` được map sang nhóm ước lượng `{food.get('display_name', food.get('id'))}`."
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
                "needs_clarification": False,
            }
        }
        reply = build_nutrition_reply(tool_results)
        return {
            "reply": reply,
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
        display_amount = f"{self._format_quantity(parsed_item.quantity)} {parsed_item.unit}"
        return {
            "display_name": food.get("display_name", food.get("name", parsed_item.name)),
            "canonical_id": food.get("id"),
            "display_amount": display_amount,
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
        if template.get("grams") is not None:
            grams_used = float(template["grams"]) * multiplier
            nutrients = self._nutrients_from_grams(food, grams_used)
        else:
            nutrients = {
                "calories": round(float(template.get("calories", 0)) * multiplier, 1),
                "protein_g": round(float(template.get("protein_g", 0)) * multiplier, 1),
                "carb_g": round(float(template.get("carb_g", 0)) * multiplier, 1),
                "fat_g": round(float(template.get("fat_g", 0)) * multiplier, 1),
            }
            grams_used = float(template.get("grams_used", 0)) * multiplier if template.get("grams_used") else None

        template_label = str(template.get("display_label", "")).strip()
        display_amount = template_label or f"{self._format_quantity(parsed_item.quantity)} {parsed_item.unit}"
        if multiplier != 1:
            display_amount = f"{self._format_quantity(parsed_item.quantity)} {parsed_item.unit}"

        return {
            "display_name": food.get("display_name", food.get("name", parsed_item.name)),
            "canonical_id": food.get("id"),
            "display_amount": display_amount,
            "grams_used": round(grams_used, 1) if grams_used is not None else None,
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
        unit = parsed_item.unit

        if unit == "g":
            return parsed_item.quantity, None
        if unit == "kg":
            return parsed_item.quantity * 1000, None

        if unit == "l":
            conversion = self.catalog.get_unit_conversion(food_id, "ml")
            if conversion is not None:
                return parsed_item.quantity * 1000 * conversion, "Dùng quy đổi 1 lít = 1000 ml."
            density = food.get("density_g_per_ml")
            if density is not None:
                return parsed_item.quantity * 1000 * float(density), "Dùng mật độ mặc định theo ml cho nguyên liệu dạng lỏng."
            return None, None

        if unit == "ml":
            conversion = self.catalog.get_unit_conversion(food_id, "ml")
            if conversion is not None:
                return parsed_item.quantity * conversion, None
            density = food.get("density_g_per_ml")
            if density is not None:
                return parsed_item.quantity * float(density), "Dùng mật độ mặc định theo ml cho nguyên liệu dạng lỏng."
            return None, None

        if unit == "qua":
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
            for keyword in ["uoc luong", "uoc tinh", "khau phan pho bien", "theo khau phan"]
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
        if float(value).is_integer():
            return str(int(value))
        return str(round(value, 2))

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
