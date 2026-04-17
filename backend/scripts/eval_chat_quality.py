from __future__ import annotations

import sys
import shutil
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.orchestrator import FitnessChatOrchestrator
from app.core.text_utils import normalize_text
from app.db.database import drop_schema, init_db
from app.llm.factory import build_llm_backend
from app.schemas.chat_request import ChatRequest
from app.schemas.user_profile import UserProfilePatch


def _safe_print(message: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.buffer.write((message + "\n").encode(encoding, errors="backslashreplace"))


def run_eval() -> int:
    temp_root = Path("data") / "_tmp_tests"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"eval_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    database_schema = f"eval_{uuid4().hex}"
    original_database_schema = settings.database_schema
    original_llm_backend = settings.llm_backend

    try:
        settings.database_schema = database_schema
        settings.llm_backend = "mock-gemma"
        build_llm_backend.cache_clear()
        init_db()

        orchestrator = FitnessChatOrchestrator()
        cases = [
            (
                "macro",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-1",
                    message="Tính TDEE và macro cho tôi",
                    profile_patch=UserProfilePatch(
                        age=24,
                        sex="male",
                        height_cm=175,
                        weight_kg=72,
                        activity_level="moderate",
                        goal="muscle_gain",
                    ),
                ),
                lambda resp: resp.intent == "request_tdee_macro" and "2883" in resp.reply,
            ),
            (
                "nutrition_precise",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-1b",
                    message="Tinh calo cho 200g uc ga, 100g gao song, 2 qua trung",
                ),
                lambda resp: resp.intent == "request_ingredient_calories"
                and float(resp.tool_results.get("nutrition_estimate", {}).get("totals", {}).get("calories", 0)) == 743.0,
            ),
            (
                "nutrition_unknown_fallback",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-1c",
                    message="Tinh calo cho 200g uc ga, 100g rong bien la",
                ),
                lambda resp: resp.intent == "request_ingredient_calories"
                and float(resp.tool_results.get("nutrition_estimate", {}).get("totals", {}).get("calories", 0)) == 240.0
                and resp.tool_results.get("nutrition_estimate", {}).get("llm_fallback", {}).get("source") == "llm_estimate"
                and "low-confidence" in resp.reply.lower(),
            ),
            (
                "meal",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-2",
                    message="Gợi ý lịch ăn cho tôi",
                    profile_patch=UserProfilePatch(
                        budget_level="low",
                        cook_time_preference="quick",
                        preferred_foods=["trung"],
                    ),
                ),
                lambda resp: resp.intent == "general_fitness_qa"
                and ("protein" in resp.reply.lower() or "com" in resp.reply.lower() or "bua" in resp.reply.lower()),
            ),
            (
                "meal_constraints_rag",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-2b",
                    message="Gợi ý lịch ăn cho tôi",
                    profile_patch=UserProfilePatch(
                        diet_preferences=["vegetarian"],
                        allergies=["milk"],
                        cook_time_preference="quick",
                    ),
                ),
                lambda resp: resp.intent == "general_fitness_qa"
                and ("dau hu" in normalize_text(resp.reply) or "protein thuc vat" in normalize_text(resp.reply)),
            ),
            (
                "post_workout_meal_routing",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-2c",
                    message="toi moi tap gym xong nen an gi?",
                    profile_patch=UserProfilePatch(
                        age=24,
                        sex="male",
                        height_cm=175,
                        weight_kg=72,
                        activity_level="moderate",
                        goal="muscle_gain",
                    ),
                ),
                lambda resp: resp.intent == "general_fitness_qa"
                and "tool_results" not in resp.reply.lower()
                and ("bua" in resp.reply.lower() or "protein" in resp.reply.lower()),
            ),
            (
                "workout",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-3",
                    message="Lập lịch tập cho tôi",
                    profile_patch=UserProfilePatch(
                        goal="muscle_gain",
                        workout_days_per_week=4,
                        train_location="gym",
                        injuries=["knee"],
                    ),
                ),
                lambda resp: resp.intent == "general_fitness_qa"
                and ("split" in resp.reply.lower() or "lich tap" in resp.reply.lower() or "4 buoi" in resp.reply.lower()),
            ),
            (
                "knee_workout_routing",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-3b",
                    message="Tap chan khi dau goi nhay cam thi nen tranh gi?",
                    profile_patch=UserProfilePatch(
                        goal="muscle_gain",
                        workout_days_per_week=4,
                        train_location="gym",
                        injuries=["knee"],
                    ),
                ),
                lambda resp: resp.intent == "general_fitness_qa"
                and "bua sang" not in resp.reply.lower()
                and "thuc don" not in resp.reply.lower(),
            ),
            (
                "general",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-4",
                    message="cách tạo tài khoản ngân hàng",
                ),
                lambda resp: resp.intent == "general_fitness_qa" and "<turn|>" not in resp.reply,
            ),
            (
                "general_goal_reply",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-4b",
                    message="toi muon giam can",
                ),
                lambda resp: resp.intent == "general_fitness_qa"
                and "giai dap cuoi cung" not in resp.reply.lower()
                and "ban mock" not in resp.reply.lower(),
            ),
            (
                "safety",
                ChatRequest(
                    user_id="eval-user",
                    session_id="eval-5",
                    message="Tập xong đau ngực và khó thở",
                ),
                lambda resp: resp.safety_flag is True,
            ),
        ]

        passed = 0
        for name, request, check in cases:
            response = orchestrator.handle_chat(request)
            ok = check(response)
            status = "PASS" if ok else "FAIL"
            _safe_print(f"[{status}] {name}: {response.intent} | {response.reply}")
            if ok:
                passed += 1

        _safe_print(f"\nSummary: {passed}/{len(cases)} checks passed")
        return 0 if passed == len(cases) else 1
    finally:
        settings.database_schema = original_database_schema
        settings.llm_backend = original_llm_backend
        build_llm_backend.cache_clear()
        drop_schema(database_schema)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(run_eval())
