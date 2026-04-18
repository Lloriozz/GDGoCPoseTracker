from __future__ import annotations

import shutil
import unittest
from uuid import uuid4
from pathlib import Path

from app.core.config import settings
from app.core.orchestrator import FitnessChatOrchestrator
from app.core.profile_extractor import extract_profile_patch_from_message
from app.core.text_utils import normalize_text
from app.db.database import get_connection, init_db
from app.llm.factory import build_llm_backend
from app.llm.gemma_local_runtime import LocalGemmaInferencer
from app.llm.mock_gemma import MockGemmaInferencer
from app.schemas.chat_request import ChatRequest
from app.schemas.user_profile import UserProfilePatch


class ChatQualityTestCase(unittest.TestCase):
    _temp_root = Path("data") / "_tmp_tests"

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_llm_backend = settings.llm_backend
        cls._original_rag_enabled = settings.rag_enabled
        cls._original_wiki_enabled = settings.wiki_enabled
        cls._original_wiki_path = settings.wiki_path
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        settings.llm_backend = cls._original_llm_backend
        settings.rag_enabled = cls._original_rag_enabled
        settings.wiki_enabled = cls._original_wiki_enabled
        settings.wiki_path = cls._original_wiki_path
        build_llm_backend.cache_clear()

    def setUp(self) -> None:
        self.temp_dir = self._temp_root / f"case_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        settings.llm_backend = "mock-gemma"
        settings.rag_enabled = True
        settings.wiki_enabled = True
        self.wiki_dir = self.temp_dir / "wiki"
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        settings.wiki_path = str(self.wiki_dir)
        build_llm_backend.cache_clear()
        init_db()
        self.orchestrator = FitnessChatOrchestrator()

    def tearDown(self) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM nutrition_clarifications")
                cursor.execute("DELETE FROM chat_turns")
                cursor.execute("DELETE FROM user_profiles")
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_macro_response_is_grounded(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="macro-user",
                session_id="macro-session",
                message="TÃ­nh TDEE vÃ  macro cho tÃ´i",
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
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertEqual(response.missing_fields, [])
        self.assertIn("workout_plan", response.tool_results)
        self.assertIn("upper/lower", normalized_reply)

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
                message="TÃ­nh TDEE vÃ  macro cho tÃ´i",
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
                message="Gá»£i Ã½ lá»‹ch Äƒn cho tÃ´i",
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertIn("meal_plan", response.tool_results)
        self.assertIn("macros", response.tool_results)
        self.assertIn("bua sang", normalized_reply)
        self.assertIn("tiet kiem", normalized_reply)
        self.assertIn("trung", normalized_reply)

    def test_meal_guidance_uses_rag_for_constraints(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="constraint-user",
                session_id="constraint-session",
                message="Gá»£i Ã½ lá»‹ch Äƒn cho tÃ´i",
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
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertIn("meal_plan", response.tool_results)
        self.assertIn("dau hu", normalized_reply)
        self.assertTrue("sua dau nanh" in normalized_reply or "protein thuc vat" in normalized_reply)

    def test_step4_rag_does_not_break_step3_meal_structure(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="meal-rag-user",
                session_id="meal-rag-session",
                message="Gá»£i Ã½ lá»‹ch Äƒn cho tÃ´i",
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
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "request_meal_guidance")
        self.assertIn("meal_plan", response.tool_results)
        self.assertIn("bua sang", normalized_reply)
        self.assertIn("bua trua", normalized_reply)
        self.assertIn("bua phu", normalized_reply)
        self.assertIn("bua toi", normalized_reply)
        self.assertNotIn("tool_results", normalized_reply)
        self.assertNotIn("response_rules", normalized_reply)

    def test_meal_rag_does_not_pull_knee_note_from_profile_injury(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="meal-injury-user",
                session_id="meal-injury-session",
                message="Gá»£i Ã½ lá»‹ch Äƒn cho tÃ´i",
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
        self.assertIn("meal_plan", response.tool_results)
        self.assertNotIn("Ä‘áº§u gá»‘i", normalized_reply)
        self.assertNotIn("rom", normalized_reply)
        self.assertNotIn("leg press", normalized_reply)

    def test_workout_plan_keeps_structure(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-user",
                session_id="workout-session",
                message="Láº­p lá»‹ch táº­p cho tÃ´i",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                    experience_level="beginner",
                    injuries=["knee"],
                ),
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertIn("workout_plan", response.tool_results)
        self.assertIn("upper/lower", normalized_reply)
        self.assertIn("buoi 1", normalized_reply)

    def test_general_chat_outside_domain_is_not_blocked(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="general-user",
                session_id="general-session",
                message="cÃ¡ch táº¡o tÃ i khoáº£n ngÃ¢n hÃ ng",
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertNotIn("<turn|>", response.reply)
        self.assertIn("ngan hang", normalized_reply)
        self.assertNotIn("protein", normalized_reply)

    def test_cost_question_gets_useful_reply(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="cost-user",
                session_id="cost-session",
                message="Äƒn nhÆ° váº­y thÃ¬ háº¿t bao nhiÃªu tiá»n 1 ngÃ y",
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("chi phi", normalized_reply)

    def test_cost_reply_respects_budget_context(self) -> None:
        self.orchestrator.handle_chat(
            ChatRequest(
                user_id="budget-user",
                session_id="budget-session-1",
                message="TÃ­nh TDEE vÃ  macro cho tÃ´i",
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
                message="Ä‚n nhÆ° váº­y thÃ¬ háº¿t bao nhiÃªu tiá»n 1 ngÃ y",
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("tiet kiem", normalized_reply)
        self.assertIn("nau nhanh", normalized_reply)

    def test_safety_red_flag_is_blocked(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="safety-user",
                session_id="safety-session",
                message="Táº­p xong tÃ´i bá»‹ Ä‘au ngá»±c vÃ  khÃ³ thá»Ÿ",
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
        self.assertIn("tang dan muc kho", normalize_text(response.reply))

    def test_wiki_supports_general_fitness_answer_for_nutrition_topics(self) -> None:
        nutrition_dir = self.wiki_dir / "nutrition"
        nutrition_dir.mkdir(parents=True, exist_ok=True)
        (nutrition_dir / "muscle-gain-principles.md").write_text(
            "# NguyÃªn Táº¯c TÄƒng CÆ¡\n\n"
            "**Summary**: Trang concept vá» nguyÃªn táº¯c tÄƒng cÆ¡ cho chatbot.\n\n"
            "**Page type**: concept\n\n"
            "**Sources**:\n"
            "- raw/top-15-foods.md\n\n"
            "**Last updated**: 2026-04-16\n\n"
            "---\n\n"
            "## Key Points\n\n"
            "- TÄƒng cÆ¡ cáº§n duy trÃ¬ protein á»•n Ä‘á»‹nh vÃ  tá»•ng nÄƒng lÆ°á»£ng há»£p má»¥c tiÃªu.\n\n"
            "## Practical Notes\n\n"
            "- CÃ³ thá»ƒ xoay tua mÃ³n Viá»‡t dá»… Äƒn háº±ng ngÃ y nhÆ° cÆ¡m, trá»©ng, á»©c gÃ  vÃ  bÃºn gÃ .\n\n"
            "## Related Pages\n\n"
            "- [[nutrition/nutrition-home]]\n",
            encoding="utf-8",
        )

        self.orchestrator = FitnessChatOrchestrator()
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="wiki-user",
                session_id="wiki-session",
                message="nguyen tac tang co la gi",
            )
        )

        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("protein", response.reply.lower())
        self.assertIn("tang co", normalize_text(response.reply))

    def test_workout_reply_uses_profile_personalization(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-personal-user",
                session_id="workout-personal-session",
                message="Láº­p lá»‹ch táº­p cho tÃ´i",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                    experience_level="beginner",
                    goal_detail="Æ°u tiÃªn giá»¯ Ä‘áº§u gá»‘i á»•n Ä‘á»‹nh",
                    injuries=["knee"],
                ),
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "request_workout_plan")
        self.assertIn("workout_plan", response.tool_results)
        self.assertIn("beginner", normalized_reply)
        self.assertIn("dau goi", normalized_reply)

    def test_step4_rag_does_not_break_step3_workout_focus(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="workout-rag-user",
                session_id="workout-rag-session",
                message="Láº­p lá»‹ch táº­p cho tÃ´i",
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
        self.assertIn("workout_plan", response.tool_results)
        self.assertNotIn("bá»¯a sÃ¡ng", normalized_reply)
        self.assertNotIn("Ä‘áº­u hÅ©", normalized_reply)
        self.assertNotIn("sá»¯a Ä‘áº­u nÃ nh", normalized_reply)


    def test_post_workout_meal_question_routes_to_meal_guidance(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="post-workout-user",
                session_id="post-workout-session",
                message="toi moi tap gym xong nen an gi?",
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
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertNotIn("tool_results", normalized_reply)
        self.assertTrue("bua" in normalized_reply or "protein" in normalized_reply)

    def test_knee_sensitive_question_routes_to_workout_path(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="knee-user",
                session_id="knee-session",
                message="Tap chan khi dau goi nhay cam thi nen tranh gi?",
                profile_patch=UserProfilePatch(
                    goal="muscle_gain",
                    workout_days_per_week=4,
                    train_location="gym",
                    injuries=["knee"],
                ),
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertIn("dau goi", normalized_reply)
        self.assertNotIn("bua sang", normalized_reply)
        self.assertNotIn("thuc don", normalized_reply)

    def test_recovery_question_stays_out_of_meal_context(self) -> None:
        response = self.orchestrator.handle_chat(
            ChatRequest(
                user_id="recovery-user",
                session_id="recovery-session",
                message="Dien giai co quan trong sau tap khong?",
            )
        )
        normalized_reply = normalize_text(response.reply)
        self.assertEqual(response.intent, "general_fitness_qa")
        self.assertTrue("hoi phuc" in normalized_reply or "ngu" in normalized_reply or "protein" in normalized_reply)
        self.assertNotIn("bua sang", normalized_reply)
        self.assertNotIn("thuc don", normalized_reply)


class MockGemmaRoutingContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MockGemmaInferencer()

    def test_llm_route_wins_over_keyword_collisions_in_general_mode(self) -> None:
        reply = self.backend.generate(
            {
                "intent": "general_fitness_qa",
                "domain_scope": "fitness",
                "message": "tap chan dau goi thi nen an gi va het bao nhieu tien 1 ngay?",
                "profile_data": {"budget_level": "low"},
                "tool_results": {},
                "kb_context": [],
                "llm_route": {"mode": "general_cost_coaching"},
            }
        )
        normalized = normalize_text(reply)
        self.assertIn("chi phi", normalized)
        self.assertNotIn("bua sang", normalized)
        self.assertNotIn("split", normalized)


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
            "message": "TÃ­nh TDEE vÃ  macro cho tÃ´i",
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
        self.assertNotIn("mock", normalize_text(grounded))

    def test_meal_guardrail_rejects_meta_response(self) -> None:
        prompt = {
            "intent": "request_meal_guidance",
            "message": "Gá»£i Ã½ lá»‹ch Äƒn cho tÃ´i",
            "profile_data": {},
            "tool_results": {
                "macros": {
                    "target_calories": 2883,
                    "protein_g": 144,
                    "fat_g": 72,
                    "carb_g": 415,
                },
                "meal_plan": {
                    "target_calories": 2883,
                    "protein_g": 144,
                    "fat_g": 72,
                    "carb_g": 415,
                    "meals": [
                        {"name": "Bua sang", "calories": 721, "protein_g": 36, "carb_g": 104, "fat_g": 18, "example": "yen mach + sua chua + chuoi"},
                        {"name": "Bua trua", "calories": 865, "protein_g": 43, "carb_g": 124, "fat_g": 22, "example": "com + uc ga + rau"},
                        {"name": "Bua phu", "calories": 433, "protein_g": 22, "carb_g": 62, "fat_g": 11, "example": "banh mi nguyen cam + trung"},
                        {"name": "Bua toi", "calories": 864, "protein_g": 43, "carb_g": 125, "fat_g": 21, "example": "com + bo nac + rau"},
                    ],
                    "notes": [],
                },
            },
        }
        grounded = self.backend._ground_response(
            "LÆ°u Ã½ quan trá»ng khi táº¡o pháº£n há»“i: hÃ£y sá»­ dá»¥ng cÃ¡c con sá»‘ trong TOOL_RESULTS.",
            prompt,
        )
        self.assertIn("bua sang", normalize_text(grounded))

    def test_general_guardrail_rejects_raw_tokens(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "Äƒn nhÆ° váº­y thÃ¬ háº¿t bao nhiÃªu tiá»n 1 ngÃ y",
            "domain_scope": "fitness",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response("```<turn|>", prompt)
        normalized = normalize_text(grounded)
        self.assertIn("ve cau hoi", normalized)
        self.assertNotIn("turn|", normalized)

    def test_workout_guardrail_rejects_internal_meta(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Láº­p lá»‹ch táº­p cho tÃ´i",
            "profile_data": {},
            "tool_results": {
                "workout_plan": {
                    "split": "upper_lower",
                    "days": [{}, {}, {}, {}],
                }
            },
        }
        grounded = self.backend._ground_response(
            "- Nháº¯c Ä‘áº¿n Ä‘iá»u chá»‰nh Ä‘áº·c biá»‡t tá»« TOOL_RESULTS náº¿u cÃ³.\n"
            "Náº¿u cÃ³ TOOL_SETTINGS thÃ¬ xem Ä‘Ã³ lÃ m dá»¯ liá»‡u Ä‘Ãºng hÆ¡n.\n"
            "HÃ£y chá»‰ tráº£ tráº£ lá»i cho ngÆ°á»i theo quy táº¯c nÃ y.",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("split", normalized)
        self.assertIn("4", grounded)

    def test_workout_prompt_uses_clean_summary_instead_of_raw_json(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Láº­p lá»‹ch táº­p cho tÃ´i",
            "profile_summary": "Má»¥c tiÃªu: muscle_gain; Sá»‘ buá»•i táº­p/tuáº§n: 4",
            "personalization_summary": "Æ¯u tiÃªn má»¥c tiÃªu chi tiáº¿t: giá»¯ Ä‘áº§u gá»‘i á»•n Ä‘á»‹nh",
            "history": [],
            "kb_context": [
                {
                    "category": "workout_injury_knee",
                    "title": "Äiá»u chá»‰nh táº­p khi nháº¡y cáº£m Ä‘áº§u gá»‘i",
                    "content": "Náº¿u Ä‘áº§u gá»‘i nháº¡y cáº£m, Æ°u tiÃªn biáº¿n thá»ƒ kiá»ƒm soÃ¡t ROM. TrÃ¡nh nhá»“i volume quÃ¡ cao.",
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
        self.assertIn("bai chinh", normalize_text(prompt_text))
        self.assertNotIn("\"days\"", prompt_text)
        self.assertNotIn("\"exercises\"", prompt_text)

    def test_workout_guardrail_rejects_channel_and_multiscript_noise(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Láº­p lá»‹ch táº­p cho tÃ´i",
            "profile_data": {},
            "tool_results": {
                "workout_plan": {
                    "split": "upper_lower",
                    "days": [{}, {}, {}, {}],
                }
            },
        }
        grounded = self.backend._ground_response(
            "Giáº£iPLAN chi tiáº¿t vá» setiap Ñ‚Ñ€ÐµÐ½Ð¸Ñ€Ð¾Ð²ÐºÐ° cho setiap Ð´ÐµÐ½ÑŒ trong káº¿ hoáº¡ch.\n"
            "Giáº£iPLAN vá» à°ªà±à°°à°¤à°¿ à°°à±‹à°œà± trong káº¿ hoáº¡ch.<channel|>ChÃ o báº¡n, Ä‘Ã¢y lÃ  káº¿ hoáº¡ch táº­p luyá»‡n chi tiáº¿t.",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("split", normalized)
        self.assertNotIn("channel|", normalized)

    def test_general_guardrail_rejects_rule_leakage(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "cÃ¡ch táº¡o tÃ i khoáº£n ngÃ¢n hÃ ng",
            "domain_scope": "out_of_domain",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "- Trá»« khi rÆ¡i vÃ o SAFETY CASE, hÃ£y tráº£ tráº£ lá»i tá»± mÃ¬nh nhÆ° má»™t trá»£ thá»§ há»¯u Ã­ch.\n"
            "- KHÃ”NG vÃ¬ thiáº¿u tool mÃ  tá»« chá»‘i giáº£i Ä‘Ã¡p.\n"
            "HÃ£y chá»‰ sá»­ dá»¥ng cÃ¡c quy táº¯c nÃ y Ä‘á»ƒ tráº£ lá»i.",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("tai khoan ngan hang", normalize_text(grounded))
        self.assertNotIn("safety case", normalized)

    def test_general_guardrail_rejects_internal_data_dump(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "cÃ¡ch táº¡o tÃ i khoáº£n ngÃ¢n hÃ ng",
            "domain_scope": "out_of_domain",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "**Dá»¯ liá»‡u:**\nIntent: general_fitness_qa\nProfile: Tuá»•i: 28\nYÃªu cáº§u hiá»‡n táº¡i cá»§a user: cÃ¡ch táº¡o tÃ i khoáº£n ngÃ¢n hÃ ng",
            prompt,
        )
        normalized = grounded.lower()
        self.assertIn("tai khoan ngan hang", normalize_text(grounded))
        self.assertNotIn("intent:", normalized)
        self.assertNotIn("dá»¯ liá»‡u", normalized)

    def test_general_guardrail_rejects_instruction_leakage_patterns_seen_in_colab(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "toi muon giam can",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "Neu co thong tin nao can thiet thi cung cap day du.\n"
            "Giai dap cuoi cung:\n"
            "Thong tin chi tiet: de giam can ban nen ket hop an uong va tap luyen.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("giam can", normalized)
        self.assertNotIn("giai dap cuoi cung", normalized)
        self.assertNotIn("thong tin chi tiet", normalized)

    def test_general_guardrail_rejects_user_context_dump_patterns(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "toi co nen tap gym khong?",
            "profile_data": {
                "goal": "muscle_gain",
                "activity_level": "moderate",
                "workout_days_per_week": 4,
                "experience_level": "beginner",
            },
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "; Kinh nghien tap: beginner.\n"
            "USER_CONTEXT: Cau hoi hien tai: toi co the tap gym khong?.\n"
            "Profile hien tai: Muc tieu: muscle_gain; Muc van dong: moderate; So buoi tap/tuan: 4.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("tap gym", normalized)
        self.assertNotIn("user_context", normalized)
        self.assertNotIn("profile hien tai", normalized)

    def test_general_guardrail_rejects_profile_final_dump_patterns(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "toi moi tap xong nen an gi gio?",
            "profile_data": {
                "goal": "muscle_gain",
            },
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            ".\n"
            "USER_CONTEXT_FINAL: Cau hoi cuoi cung: Toi muon an gi sau khi tap luyen?\n"
            "PROFILE_FINAL: Muc tieu: muscle_gain; Thoi gian_chuan_bi: quick.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertTrue("bua" in normalized or "recovery" in normalized or "tap xong" in normalized)
        self.assertNotIn("user_context_final", normalized)
        self.assertNotIn("profile_final", normalized)

    def test_general_guardrail_rejects_reference_dump_patterns(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "toi dang giam can toi nen an gi?",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            ".\n"
            "Thongtin tham khao lien quan:\n"
            "MEDLATEC nhan manh viec duy tri bua toi giam can nen uu tien chat xo.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("giam can", normalized)
        self.assertNotIn("thongtin tham khao", normalized)
        self.assertNotIn("medlatec", normalized)

    def test_general_guardrail_uses_safe_fallback_instead_of_mock_disclaimer(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "cach tao tai khoan ngan hang",
            "domain_scope": "out_of_domain",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "Minh da nhan duoc cau hoi nay. O ban mock nay, minh giu cau tra loi o muc tong quat.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("tai khoan ngan hang", normalized)
        self.assertNotIn("ban mock", normalized)

    def test_general_guardrail_rejects_instruction_dump_for_recovery_question(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "dien giai co quan trong voi tap the thao khong",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "KHONG NHAC DEN BAT TRUNG, TOOL, RESPONSE RULES, INTENTION HAY NHAN NOI BO.\n"
            "TRA LOI BANG TIENG VIET TU NHIEN VA KHONG VIET CAC NHAN NOI BO.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("dien giai", normalized)
        self.assertNotIn("response rules", normalized)
        self.assertNotIn("khong nhac den", normalized)

    def test_general_guardrail_rejects_role_prefixed_echo_for_phone_question(self) -> None:
        prompt = {
            "intent": "general_fitness_qa",
            "message": "toi muon mua dien thoai nen lam gi",
            "domain_scope": "out_of_domain",
            "profile_data": {},
            "tool_results": {},
        }
        grounded = self.backend._ground_response(
            "USER:** toi muon mua dien thoai nen lam gi?",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("dien thoai", normalized)
        self.assertNotIn("user:", normalized)

    def test_workout_guardrail_rejects_meal_contamination(self) -> None:
        prompt = {
            "intent": "request_workout_plan",
            "message": "Tap chan khi dau goi nhay cam thi nen tranh gi?",
            "profile_data": {},
            "tool_results": {
                "workout_plan": {
                    "split": "upper_lower",
                    "days": [{}, {}, {}, {}],
                }
            },
        }
        grounded = self.backend._ground_response(
            "Neu dau goi nhay cam, uu tien ROM co kiem soat. Bua sang nen an yen mach va bua toi nen them ga.",
            prompt,
        )
        normalized = normalize_text(grounded)
        self.assertIn("split", normalized)
        self.assertNotIn("bua sang", normalized)

    def test_general_user_prompt_is_minimal(self) -> None:
        prompt_text = self.backend._build_user_prompt(
            {
                "intent": "general_fitness_qa",
                "message": "cach tao tai khoan ngan hang",
                "domain_scope": "out_of_domain",
                "profile_summary": "Tuá»•i: 28; Chiá»u cao: 178 cm",
                "personalization_summary": "Æ¯u tiÃªn tráº£ lá»i ngáº¯n gá»n",
                "history": [],
                "kb_context": [],
                "tool_results": {},
            }
        )
        normalized = normalize_text(prompt_text)
        self.assertIn("cach tao tai khoan ngan hang", normalized)
        self.assertNotIn("cau hoi hien tai", normalized)
        self.assertNotIn("profile lien quan", normalized)
        self.assertNotIn("thong tin tham khao", normalized)
        self.assertNotIn("intent:", normalized)
        self.assertNotIn("profile:", normalized)
        self.assertNotIn("day la du lieu", normalized)
        self.assertNotIn("tuoi", normalized)

    def test_general_user_prompt_obeys_orchestrator_route_flags(self) -> None:
        prompt_text = self.backend._build_user_prompt(
            {
                "intent": "general_fitness_qa",
                "message": "toi muon mua dien thoai nen lam gi",
                "domain_scope": "fitness",
                "profile_summary": "Tuoi: 28; Chieu cao: 178 cm",
                "history": [{"user_message": "cuoc hoi truoc", "assistant_message": "phan hoi truoc"}],
                "kb_context": [{"title": "Workout", "content": "Tang dan muc kho theo thoi gian."}],
                "tool_results": {},
                "llm_route": {
                    "mode": "general_out_of_domain",
                    "prompt_style": "general_minimal",
                    "include_profile_context": False,
                    "include_history_context": False,
                    "include_kb_context": False,
                },
            }
        )
        normalized = normalize_text(prompt_text)
        self.assertIn("mua dien thoai", normalized)
        self.assertNotIn("tuoi", normalized)
        self.assertNotIn("cuoc hoi truoc", normalized)
        self.assertNotIn("tang dan muc kho", normalized)

    def test_general_system_prompt_discourages_template_completion(self) -> None:
        prompt_text = self.backend._build_system_prompt(
            {
                "intent": "general_fitness_qa",
                "system_prompt": "",
            }
        )
        normalized = normalize_text(prompt_text)
        self.assertIn("khong dien tiep mau prompt", normalized)
        self.assertIn("khong lap lai", normalized)
        self.assertNotIn("tool_results", normalized)

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


class LocalGemmaDeviceRoutingTestCase(unittest.TestCase):
    class _FakeParameter:
        def __init__(self, device: str) -> None:
            self.device = device

    class _FakeModel:
        def __init__(self, *, parameter_device: str, hf_device_map: dict[str, object] | None = None) -> None:
            self._parameter_device = parameter_device
            if hf_device_map is not None:
                self.hf_device_map = hf_device_map

        def parameters(self):
            yield LocalGemmaDeviceRoutingTestCase._FakeParameter(self._parameter_device)

    def setUp(self) -> None:
        self.backend = LocalGemmaInferencer(
            model_id="google/gemma-4-E4B-it",
            device="cuda",
            dtype="bfloat16",
            quantization="4bit",
            max_new_tokens=128,
            temperature=0.3,
            top_p=0.95,
            do_sample=False,
            trust_remote_code=False,
            cpu_offload=True,
            offload_buffers=True,
            gpu_memory_limit_mb=12000,
            cpu_memory_limit_mb=16384,
        )

    def test_prefers_cuda_from_hf_device_map_for_inputs(self) -> None:
        self.backend._model = self._FakeModel(
            parameter_device="cpu",
            hf_device_map={"model.embed_tokens": "cuda:0", "lm_head": "cpu"},
        )

        self.assertEqual(self.backend._get_model_device(), "cuda:0")

    def test_falls_back_to_parameter_device_without_hf_device_map(self) -> None:
        self.backend._model = self._FakeModel(parameter_device="cpu")

        self.assertEqual(self.backend._get_model_device(), "cpu")

if __name__ == "__main__":
    unittest.main()
