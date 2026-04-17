from __future__ import annotations

import shutil
import unittest
from uuid import uuid4
from pathlib import Path

from app.core.config import settings
from app.core.orchestrator import FitnessChatOrchestrator
from app.core.profile_extractor import extract_profile_patch_from_message
from app.core.prompt_builder import build_system_prompt
from app.core.text_utils import normalize_text
from app.db.database import init_db
from app.llm.factory import build_llm_backend
from app.llm.gemma_local import LocalGemmaInferencer
from app.schemas.chat_request import ChatRequest
from app.schemas.user_profile import UserProfilePatch


class ChatQualityTestCase(unittest.TestCase):
    _temp_root = Path("data") / "_tmp_tests"

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_sqlite_path = settings.sqlite_path
        cls._original_llm_backend = settings.llm_backend
        cls._original_rag_enabled = settings.rag_enabled
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        settings.sqlite_path = cls._original_sqlite_path
        settings.llm_backend = cls._original_llm_backend
        settings.rag_enabled = cls._original_rag_enabled
        build_llm_backend.cache_clear()

    def setUp(self) -> None:
        self.temp_dir = self._temp_root / f"case_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        settings.sqlite_path = str(self.temp_dir / "test.db")
        settings.llm_backend = "mock-gemma"
        settings.rag_enabled = True
        build_llm_backend.cache_clear()
        init_db()
        self.orchestrator = FitnessChatOrchestrator()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_macro_response_is_grounded(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="macro-user",
                session_id="macro-session",
                message="Tính TDEE và macro cho tôi",
                profile_patch=UserProfilePatch(
                    age=24,
                    sex="male",
                    height_cm=175,
                    weight_kg=72,
                    activity_level="moderate",
                    goal="muscle_gain",
                ),
            )
        )
        self.assertEqual(response.intent, "request_tdee_macro")
        self.assertIn("2883", response.reply)
        self.assertIn("144g", response.reply)
        self.assertIn("macros", response.tool_results)

    def test_profile_extractor_reads_common_fitness_fields_from_message(self) -> None:
        patch = extract_profile_patch_from_message(
            "Toi nam, 24 tuoi, cao 175cm, nang 72kg, tap 4 buoi moi tuan o gym. Muc tieu tang co."
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual(patch.sex, "male")
        self.assertEqual(patch.age, 24)
        self.assertEqual(patch.height_cm, 175)
        self.assertEqual(patch.weight_kg, 72)
        self.assertEqual(patch.workout_days_per_week, 4)
        self.assertEqual(patch.train_location, "gym")
        self.assertEqual(patch.goal, "muscle_gain")
        self.assertEqual(patch.activity_level, "moderate")

    def test_natural_language_tdee_request_is_not_misclassified_as_nutrition(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="macro-nl-user",
                session_id="macro-nl-session",
                message=(
                    "Toi nam, 24 tuoi, cao 175cm, nang 72kg, tap 4 buoi moi tuan o gym. "
                    "Muc tieu tang co. Hay tinh TDEE va goi y macro cho toi."
                ),
            )
        )
        self.assertEqual(response.intent, "request_tdee_macro")
        self.assertEqual(response.missing_fields, [])
        self.assertIn("macros", response.tool_results)

    def test_natural_language_workout_request_uses_extracted_profile(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-nl-user",
                session_id="workout-nl-session",
                message="Tao lich tap cho toi, toi tap 4 buoi moi tuan o gym va muc tieu tang co.",
            )
        )
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertEqual(response.missing_fields, [])
        self.assertIn("workout_plan", response.tool_results)

    def test_nutrition_precise_request_returns_deterministic_result(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="nutrition-user",
                session_id="nutrition-session-1",
                message="Tinh calo cho 200g uc ga, 100g gao song, 2 qua trung",
            )
        )
        estimate = response.tool_results.get("nutrition_estimate", {})
        self.assertEqual(response.intent, "request_ingredient_calories")
        self.assertIn("Tong:", response.reply)
        self.assertEqual(estimate.get("mode"), "precise")
        self.assertAlmostEqual(float(estimate.get("totals", {}).get("calories", 0)), 743.0)

    def test_nutrition_ambiguous_request_asks_then_resolves_estimate(self) -> None:
        first = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="nutrition-user",
                session_id="nutrition-session-2",
                message="Tinh calo cho 1 bat com, 1 phan pho",
            )
        )
        self.assertEqual(first.intent, "request_ingredient_calories")
        self.assertTrue(first.tool_results["nutrition_estimate"]["needs_clarification"])
        self.assertIn("khau phan pho bien", first.reply.lower())

        second = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="nutrition-user",
                session_id="nutrition-session-2",
                message="Uoc luong giup minh",
            )
        )
        estimate = second.tool_results.get("nutrition_estimate", {})
        self.assertEqual(second.intent, "request_ingredient_calories")
        self.assertEqual(estimate.get("mode"), "estimated")
        self.assertAlmostEqual(float(estimate.get("totals", {}).get("calories", 0)), 688.0)

    def test_nutrition_pending_clarification_is_ignored_after_topic_change(self) -> None:
        self.orchestrator.handle_chat(
            ChatRequest(
                user_id="nutrition-user",
                session_id="nutrition-session-3",
                message="Tinh calo cho 1 bat com, 1 phan pho",
            )
        )
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="nutrition-user",
                session_id="nutrition-session-3",
                message="Lap lich tap cho toi",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                ),
            )
        )
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertIn("workout_plan", response.tool_results)

    def test_nutrition_partial_unmatched_still_returns_matched_totals(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="nutrition-user",
                session_id="nutrition-session-4",
                message="Tinh calo cho 200g uc ga, 100g rong bien la",
            )
        )
        estimate = response.tool_results.get("nutrition_estimate", {})
        self.assertEqual(response.intent, "request_ingredient_calories")
        self.assertEqual(estimate.get("unmatched_items"), ["rong bien la"])
        self.assertEqual(estimate.get("unmatched_inputs"), ["100g rong bien la"])
        self.assertAlmostEqual(float(estimate.get("totals", {}).get("calories", 0)), 240.0)
        self.assertIn("rong bien la", response.reply.lower())
        self.assertIn("low-confidence", response.reply.lower())
        self.assertEqual(estimate.get("llm_fallback", {}).get("source"), "llm_estimate")

    def test_meal_guidance_uses_profile_preferences(self) -> None:
        self.orchestrator.handle_chat(
            ChatRequest(
                user_id="meal-user",
                session_id="meal-session-1",
                message="Tính TDEE và macro cho tôi",
                profile_patch=UserProfilePatch(
                    age=24,
                    sex="male",
                    height_cm=175,
                    weight_kg=72,
                    activity_level="moderate",
                    goal="muscle_gain",
                    budget_level="low",
                    cook_time_preference="quick",
                    preferred_foods=["pho", "trung"],
                    disliked_foods=["ca hoi"],
                ),
            )
        )
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="meal-user",
                session_id="meal-session-2",
                message="Gợi ý lịch ăn cho tôi",
            )
        )
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertIn("Bữa sáng", response.reply)
        self.assertIn("tiết kiệm", response.reply.lower())
        self.assertIn("trứng", response.reply.lower())

    def test_meal_guidance_uses_rag_for_constraints(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="constraint-user",
                session_id="constraint-session",
                message="Gợi ý lịch ăn cho tôi",
                profile_patch=UserProfilePatch(
                    age=24,
                    sex="female",
                    height_cm=162,
                    weight_kg=54,
                    activity_level="light",
                    goal="maintenance",
                    diet_preferences=["vegetarian"],
                    allergies=["milk"],
                    cook_time_preference="quick",
                ),
            )
        )
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertIn("đậu hũ", response.reply.lower())
        self.assertTrue(
            "sữa đậu nành" in response.reply.lower() or "protein thực vật" in response.reply.lower()
        )

    def test_step4_rag_does_not_break_step3_meal_structure(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="meal-rag-user",
                session_id="meal-rag-session",
                message="Gợi ý lịch ăn cho tôi",
                profile_patch=UserProfilePatch(
                    age=24,
                    sex="male",
                    height_cm=175,
                    weight_kg=72,
                    activity_level="moderate",
                    goal="muscle_gain",
                    budget_level="low",
                    cook_time_preference="quick",
                ),
            )
        )
        normalized_reply = response.reply.lower()
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertIn("bữa sáng", normalized_reply)
        self.assertIn("bữa trưa", normalized_reply)
        self.assertIn("bữa phụ", normalized_reply)
        self.assertIn("bữa tối", normalized_reply)
        self.assertNotIn("tool_results", normalized_reply)
        self.assertNotIn("response_rules", normalized_reply)

    def test_meal_rag_does_not_pull_knee_note_from_profile_injury(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="meal-injury-user",
                session_id="meal-injury-session",
                message="Gợi ý lịch ăn cho tôi",
                profile_patch=UserProfilePatch(
                    age=24,
                    sex="male",
                    height_cm=175,
                    weight_kg=72,
                    activity_level="moderate",
                    goal="muscle_gain",
                    budget_level="low",
                    cook_time_preference="quick",
                    injuries=["knee"],
                ),
            )
        )
        normalized_reply = response.reply.lower()
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertNotIn("đầu gối", normalized_reply)
        self.assertNotIn("rom", normalized_reply)
        self.assertNotIn("leg press", normalized_reply)

    def test_workout_plan_keeps_structure(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-user",
                session_id="workout-session",
                message="Lập lịch tập cho tôi",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                    experience_level="beginner",
                    injuries=["knee"],
                ),
            )
        )
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertIn("workout_plan", response.tool_results)
        self.assertEqual(response.tool_results["workout_plan"]["split"], "upper_lower")

    def test_general_chat_outside_domain_is_not_blocked(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="general-user",
                session_id="general-session",
                message="cách tạo tài khoản ngân hàng",
            )
        )
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertNotIn("<turn|>", response.reply)
        self.assertIn("tài khoản ngân hàng", response.reply.lower())
        self.assertNotIn("protein", response.reply.lower())

    def test_cost_question_gets_useful_reply(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="cost-user",
                session_id="cost-session",
                message="ăn như vậy thì hết bao nhiêu tiền 1 ngày",
            )
        )
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("chi phí", response.reply.lower())

    def test_cost_reply_respects_budget_context(self) -> None:
        self.orchestrator.handle_chat(
            ChatRequest(
                user_id="budget-user",
                session_id="budget-session-1",
                message="Tính TDEE và macro cho tôi",
                profile_patch=UserProfilePatch(
                    age=24,
                    sex="male",
                    height_cm=175,
                    weight_kg=72,
                    activity_level="moderate",
                    goal="muscle_gain",
                    budget_level="low",
                    cook_time_preference="quick",
                ),
            )
        )
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="budget-user",
                session_id="budget-session-2",
                message="Ăn như vậy thì hết bao nhiêu tiền 1 ngày",
            )
        )
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("tiết kiệm", response.reply.lower())
        self.assertIn("nấu nhanh", response.reply.lower())

    def test_safety_red_flag_is_blocked(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="safety-user",
                session_id="safety-session",
                message="Tập xong tôi bị đau ngực và khó thở",
            )
        )
        self.assertTrue(response.safety_flag)
        self.assertEqual(response.intent, "unsafe_medical_case")

    def test_rag_supports_general_fitness_answer(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="rag-user",
                session_id="rag-session",
                message="progressive overload la gi",
            )
        )
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("tăng dần mức khó", response.reply.lower())

    def test_workout_reply_uses_profile_personalization(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-personal-user",
                session_id="workout-personal-session",
                message="Lập lịch tập cho tôi",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                    experience_level="beginner",
                    goal_detail="ưu tiên giữ đầu gối ổn định",
                    injuries=["knee"],
                ),
            )
        )
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertIn("beginner", response.reply.lower())
        self.assertIn("đầu gối", response.reply.lower())

    def test_step4_rag_does_not_break_step3_workout_focus(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-rag-user",
                session_id="workout-rag-session",
                message="Lập lịch tập cho tôi",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                    injuries=["knee"],
                    diet_preferences=["vegetarian"],
                    allergies=["milk"],
                ),
            )
        )
        normalized_reply = response.reply.lower()
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertEqual(response.tool_results["workout_plan"]["split"], "upper_lower")
        self.assertNotIn("bữa sáng", normalized_reply)
        self.assertNotIn("đậu hũ", normalized_reply)
        self.assertNotIn("sữa đậu nành", normalized_reply)


class LocalGemmaGuardrailTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = LocalGemmaInferencer(
            model_id="dummy",
            device="cpu",
            dtype="float32",
            quantization="none",
            max_new_tokens=64,
            temperature=0.2,
            top_p=0.9,
            do_sample=False,
            trust_remote_code=False,
            cpu_offload=True,
            offload_buffers=True,
            gpu_memory_limit_mb=3500,
            cpu_memory_limit_mb=16384,
        )

    def test_macro_guardrail_falls_back_when_numbers_change(self) -> None:
        prompt = {
            "intent": "request_tdee_macro",
            "message": "Tính TDEE và macro cho tôi",
            "profile_data": {},
            "tool_results": {
                "macros": {
                    "target_calories": 2883,
                    "protein_g": 144,
                    "fat_g": 72,
                    "carb_g": 415,
                }
            },
        }
        grounded = self.backend._ground_response(
            "Final Answer: 2890 kcal, 145g protein, 72g fat, 416g carb.",
            prompt,
        )
        self.assertIn("2883", grounded)

    def test_meal_guardrail_rejects_meta_response(self) -> None:
        prompt = {
            "intent": "request_meal_guidance",
            "message": "Gợi ý lịch ăn cho tôi",
            "profile_data": {},
            "tool_results": {
                "macros": {
                    "target_calories": 2883,
                    "protein_g": 144,
                    "fat_g": 72,
                    "carb_g": 415,
                }
            },
        }
        grounded = self.backend._ground_response(
            "Lưu ý quan trọng khi tạo phản hồi: hãy sử dụng các con số trong TOOL_RESULTS.",
            prompt,
        )
        self.assertIn("Bữa sáng", grounded)

    def test_general_guardrail_rejects_raw_tokens(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "ăn như vậy thì hết bao nhiêu tiền 1 ngày",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response("```<turn|>", prompt)
        self.assertIn("chi phí", grounded.lower())

    def test_workout_guardrail_rejects_internal_meta(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Lập lịch tập cho tôi",
            "profile_data": {},
            "tool_results": {
                "workout_plan": {
                    "split": "upper_lower",
                    "days": [{}, {}, {}, {}],
                }
            },
        }
        grounded = self.backend._ground_response(
            "- Nhắc đến điều chỉnh đặc biệt từ TOOL_RESULTS nếu có.\n"
            "Nếu có TOOL_SETTINGS thì xem đó làm dữ liệu đúng hơn.\n"
            "Hãy chỉ trả trả lời cho người theo quy tắc này.",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("split", normalized)
        self.assertIn("4", grounded)

    def test_workout_prompt_uses_clean_summary_instead_of_raw_json(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Lập lịch tập cho tôi",
            "profile_summary": "Mục tiêu: muscle_gain; Số buổi tập/tuần: 4",
            "personalization_summary": "Ưu tiên mục tiêu chi tiết: giữ đầu gối ổn định",
            "history": [],
            "kb_context": [
                {
                    "category": "workout_injury_knee",
                    "title": "Điều chỉnh tập khi nhạy cảm đầu gối",
                    "content": "Nếu đầu gối nhạy cảm, ưu tiên biến thể kiểm soát ROM. Tránh nhồi volume quá cao.",
                }
            ],
            "tool_results": {
                "workout_plan": {
                    "split": "upper_lower",
                    "goal": "muscle_gain",
                    "train_location": "gym",
                    "days": [
                        {
                            "day": "Day 1",
                            "focus": "Upper",
                            "exercises": [
                                {"name": "Barbell Bench Press"},
                                {"name": "Lat Pulldown"},
                                {"name": "Cable Row"},
                            ],
                        }
                    ],
                    "notes": ["Reduced knee-stress exercise selection"],
                }
            },
        }
        prompt_text = self.backend._build_user_prompt(prompt)
        normalized = prompt_text.lower()
        self.assertIn("split: upper_lower", normalized)
        self.assertIn("bài chính", normalized)
        self.assertNotIn("\"days\"", prompt_text)
        self.assertNotIn("\"exercises\"", prompt_text)

    def test_workout_guardrail_rejects_channel_and_multiscript_noise(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Lập lịch tập cho tôi",
            "profile_data": {},
            "tool_results": {
                "workout_plan": {
                    "split": "upper_lower",
                    "days": [{}, {}, {}, {}],
                }
            },
        }
        grounded = self.backend._ground_response(
            "GiảiPLAN chi tiết về setiap тренировка cho setiap день trong kế hoạch.\n"
            "GiảiPLAN về ప్రతి రోజు trong kế hoạch.<channel|>Chào bạn, đây là kế hoạch tập luyện chi tiết.",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("split", normalized)
        self.assertNotIn("channel|", normalized)

    def test_general_guardrail_rejects_rule_leakage(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "cách tạo tài khoản ngân hàng",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "- Trừ khi rơi vào SAFETY CASE, hãy trả trả lời tự mình như một trợ thủ hữu ích.\n"
            "- KHÔNG vì thiếu tool mà từ chối giải đáp.\n"
            "Hãy chỉ sử dụng các quy tắc này để trả lời.",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("tài khoản ngân hàng", normalized)
        self.assertNotIn("safety case", normalized)

    def test_general_guardrail_rejects_internal_data_dump(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "cách tạo tài khoản ngân hàng",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "**Dữ liệu:**\nIntent: general_fitness_qa\nProfile: Tuổi: 28\nYêu cầu hiện tại của user: cách tạo tài khoản ngân hàng",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("tài khoản ngân hàng", normalized)
        self.assertNotIn("intent:", normalized)
        self.assertNotIn("dữ liệu", normalized)

    def test_general_user_prompt_is_minimal(self) -> None:
        prompt_text = self.backend._build_user_prompt(
            {
                "intent": "general_fitness_qa",
                "message": "cách tạo tài khoản ngân hàng",
                "profile_summary": "Tuổi: 28; Chiều cao: 178 cm",
                "personalization_summary": "Ưu tiên trả lời ngắn gọn",
                "history": [],
                "kb_context": [],
                "tool_results": {},
            }
        )
        normalized = normalize_text(prompt_text)
        self.assertIn("cau hoi hien tai", normalized)
        self.assertNotIn("intent:", normalized)
        self.assertNotIn("profile:", normalized)
        self.assertNotIn("day la du lieu", normalized)

    def test_nutrition_fallback_prompt_is_minimal(self) -> None:
        prompt_text = self.backend._build_user_prompt(
            {
                "intent": "nutrition_llm_fallback",
                "message": "Tinh calo cho 200g uc ga, 100g rong bien la",
                "nutrition_fallback_items": ["100g rong bien la"],
                "nutrition_known_totals": {
                    "calories": 240.0,
                    "protein_g": 46.0,
                    "carb_g": 0.0,
                    "fat_g": 5.2,
                },
                "history": [],
                "kb_context": [],
            }
        )
        normalized = normalize_text(prompt_text)
        self.assertIn("cac muc chua co trong catalog", normalized)
        self.assertIn("100g rong bien la", normalized)
        self.assertNotIn("intent:", normalized)
        self.assertNotIn("profile:", normalized)

    def test_nutrition_fallback_guardrail_rejects_internal_meta(self) -> None:
        prompt = {
            "intent": "nutrition_llm_fallback",
            "message": "Tinh calo cho 200g uc ga, 100g rong bien la",
            "nutrition_fallback_items": ["100g rong bien la"],
            "nutrition_known_totals": {"calories": 240.0},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "Intent: nutrition_llm_fallback\nTool_results: ...\nHay chi tra loi theo quy tac nay.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("low-confidence", normalized)
        self.assertIn("rong bien", normalized)

    def test_general_system_prompt_uses_helpful_assistant_persona(self) -> None:
        system_prompt = self.backend._build_system_prompt(
            {
                "intent": "general_fitness_qa",
                "system_prompt": build_system_prompt("general_fitness_qa"),
            }
        )
        normalized = system_prompt.lower()
        self.assertIn("trợ lý hữu ích", normalized)
        self.assertNotIn("trợ lý fitness", normalized)
        self.assertNotIn("ưu tiên fitness khi câu hỏi liên quan", normalized)

    def test_fitness_system_prompt_keeps_fitness_persona(self) -> None:
        system_prompt = self.backend._build_system_prompt(
            {
                "intent": "request_workout_plan",
                "system_prompt": build_system_prompt("request_workout_plan"),
            }
        )
        normalized = system_prompt.lower()
        self.assertIn("trợ lý fitness", normalized)
        self.assertNotIn("không cố lái câu trả lời về fitness", normalized)


if __name__ == "__main__":
    unittest.main()
