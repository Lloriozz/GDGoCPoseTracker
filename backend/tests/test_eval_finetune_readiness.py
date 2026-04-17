from __future__ import annotations

import unittest

from app.schemas.chat_response import ChatResponse
from scripts.eval_finetune_readiness import (
    EvalFailure,
    EvalResult,
    _recommend_next_step,
    _validate_general,
    _validate_macro,
    _validate_meal,
    _validate_nutrition,
    _validate_vietnamese_quality,
)


class FineTuneEvalTestCase(unittest.TestCase):
    def test_macro_validator_accepts_grounded_reply(self) -> None:
        response = ChatResponse(
            session_id="macro-session",
            reply="Mức calories mục tiêu của bạn hiện là 2883 kcal/ngày, với 144g protein, 72g fat và 415g carb.",
            intent="request_tdee_macro",
            safety_flag=False,
            missing_fields=[],
            tool_results={
                "macros": {
                    "target_calories": 2883,
                    "protein_g": 144,
                    "fat_g": 72,
                    "carb_g": 415,
                }
            },
        )
        self.assertEqual(_validate_macro(response), [])

    def test_meal_validator_rejects_injury_contamination(self) -> None:
        response = ChatResponse(
            session_id="meal-session",
            reply="Bữa sáng: yến mạch. Bữa trưa: cơm gà. Lưu ý đầu gối, ưu tiên ROM thấp và leg press nhẹ.",
            intent="request_meal_guidance",
            safety_flag=False,
            missing_fields=[],
            tool_results={"macros": {"target_calories": 2883}},
        )
        failures = _validate_meal(response)
        self.assertTrue(any(failure.code == "meal_contamination" for failure in failures))

    def test_nutrition_validator_accepts_grounded_reply(self) -> None:
        response = ChatResponse(
            session_id="nutrition-session",
            reply="Minh da tinh dinh duong cho phan ban nhap.\nTong: 743 kcal | 64.4g protein | 80.4g carb | 15.3g fat",
            intent="request_ingredient_calories",
            safety_flag=False,
            missing_fields=[],
            tool_results={
                "nutrition_estimate": {
                    "mode": "precise",
                    "totals": {
                        "calories": 743.0,
                        "protein_g": 64.4,
                        "carb_g": 80.4,
                        "fat_g": 15.3,
                    }
                }
            },
        )
        self.assertEqual(_validate_nutrition(response), [])

    def test_general_validator_rejects_fitness_leak(self) -> None:
        response = ChatResponse(
            session_id="general-session",
            reply="Cách tạo tài khoản ngân hàng cũng tương tự như lên macro và meal plan.",
            intent="general_fitness_qa",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        failures = _validate_general(response)
        self.assertTrue(any(failure.code == "fitness_leak" for failure in failures))

    def test_vietnamese_quality_detects_mojibake(self) -> None:
        response = ChatResponse(
            session_id="encoding-session",
            reply="MÃ¬nh goi y lich an cho ban.",
            intent="general_fitness_qa",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        failures = _validate_vietnamese_quality(response)
        self.assertTrue(any(failure.code == "encoding_broken" for failure in failures))

    def test_recommendation_blocks_fine_tune_when_functional_failures_exist(self) -> None:
        results = [
            EvalResult(
                name="macro_grounded",
                group="functional",
                ok=False,
                failures=[EvalFailure(code="wrong_numbers", message="wrong")],
                intent="request_tdee_macro",
                reply="...",
                elapsed_seconds=0.1,
            )
        ]
        recommendation = _recommend_next_step(results)
        self.assertIn("Chưa nên fine-tune", recommendation)


if __name__ == "__main__":
    unittest.main()
