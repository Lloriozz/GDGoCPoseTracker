from __future__ import annotations

import unittest

from app.schemas.chat_response import ChatResponse
from scripts.smoke_eval_gemma import (
    _is_general_pass,
    _is_goal_coaching_pass,
    _is_macro_pass,
    _is_meal_pass,
    _is_nutrition_pass,
    _is_post_workout_meal_pass,
    _is_recovery_pass,
    _is_safety_pass,
    _is_knee_workout_pass,
    _is_workout_pass,
)


class SmokeEvalGemmaTestCase(unittest.TestCase):
    def test_macro_check_requires_grounded_numbers(self) -> None:
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
        self.assertTrue(_is_macro_pass(response))

    def test_meal_check_rejects_workout_contamination(self) -> None:
        response = ChatResponse(
            session_id="meal-session",
            reply=(
                "Bữa sáng: yến mạch. Bữa trưa: cơm gà. "
                "Lưu ý đầu gối, ưu tiên ROM thấp và leg press nhẹ."
            ),
            intent="request_tdee_macro",
            safety_flag=False,
            missing_fields=[],
            tool_results={"macros": {"target_calories": 2883}},
        )
        self.assertFalse(_is_meal_pass(response))

    def test_nutrition_check_requires_exact_tool_totals(self) -> None:
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
        self.assertTrue(_is_nutrition_pass(response))

    def test_workout_check_rejects_channel_noise(self) -> None:
        response = ChatResponse(
            session_id="workout-session",
            reply="GiảiPLAN về lịch tập.<channel|>Chào bạn",
            intent="general_fitness_qa",
            safety_flag=False,
            missing_fields=[],
            tool_results={"workout_plan": {"split": "upper_lower", "days": [{}, {}, {}, {}]}},
        )
        self.assertFalse(_is_workout_pass(response))

    def test_general_check_rejects_fitness_leak(self) -> None:
        response = ChatResponse(
            session_id="general-session",
            reply="Cách tạo tài khoản ngân hàng cũng tương tự như thiết lập macro và meal plan.",
            intent="request_tdee_macro",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        self.assertFalse(_is_general_pass(response))

    def test_safety_check_requires_real_red_flag_response(self) -> None:
        response = ChatResponse(
            session_id="safety-session",
            reply="Bạn nên dừng tập ngay và đi khám sớm để được đánh giá trực tiếp.",
            intent="unsafe_medical_case",
            safety_flag=True,
            missing_fields=[],
            tool_results={},
        )
        self.assertTrue(_is_safety_pass(response))


    def test_goal_coaching_check_requires_clean_weight_loss_answer(self) -> None:
        response = ChatResponse(
            session_id="goal-session",
            reply="De giam can ben vung, ban nen giu tham hut calo vua phai, uu tien protein on dinh va tap deu.",
            intent="general_fitness_qa",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        self.assertTrue(_is_goal_coaching_pass(response))

    def test_post_workout_meal_check_rejects_wrong_intent(self) -> None:
        response = ChatResponse(
            session_id="meal-session-2",
            reply="Sau tap ban nen uu tien protein va carb de hoi phuc.",
            intent="request_tdee_macro",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        self.assertFalse(_is_post_workout_meal_pass(response))

    def test_recovery_check_rejects_meal_contamination(self) -> None:
        response = ChatResponse(
            session_id="recovery-session",
            reply="Dien giai quan trong sau tap, nhung bua sang va bua toi cua ban cung can tinh lai.",
            intent="general_fitness_qa",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        self.assertFalse(_is_recovery_pass(response))

    def test_knee_workout_check_rejects_meal_contamination(self) -> None:
        response = ChatResponse(
            session_id="knee-session",
            reply="Lich tap cho dau goi nhay cam, dong thoi bua sang nen co yen mach va trung.",
            intent="general_fitness_qa",
            safety_flag=False,
            missing_fields=[],
            tool_results={},
        )
        self.assertFalse(_is_knee_workout_pass(response))


if __name__ == "__main__":
    unittest.main()
