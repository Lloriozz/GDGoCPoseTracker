from app.core.config import settings
from app.core.profile_extractor import extract_profile_patch_from_message, merge_profile_patches
from app.core.prompt_builder import (
    build_personalization_summary,
    build_profile_summary,
    build_system_prompt,
)
from app.core.safety import SafetyChecker
from app.core.text_utils import normalize_text
from app.llm.factory import build_llm_backend
from app.memory.chat_history import ChatHistoryStore
from app.memory.nutrition_clarification_store import NutritionClarificationStore
from app.memory.profile_store import ProfileStore
from app.rag.retriever import KnowledgeRetriever
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse
from app.tools.macros import calculate_macros
from app.tools.nutrition_calculator import (
    NutritionCalculator,
    build_nutrition_reply,
    looks_like_nutrition_request,
)
from app.tools.tdee import calculate_tdee
from app.tools.workout_plan import generate_workout_plan


class FitnessChatOrchestrator:
    def __init__(self) -> None:
        self.profile_store = ProfileStore()
        self.chat_history = ChatHistoryStore(max_messages=settings.max_history_messages)
        self.nutrition_clarifications = NutritionClarificationStore()
        self.safety_checker = SafetyChecker()
        self.retriever = KnowledgeRetriever()
        self.nutrition_calculator = NutritionCalculator()
        self.llm = build_llm_backend()

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        inferred_patch = extract_profile_patch_from_message(request.message)
        effective_patch = merge_profile_patches(inferred_patch, request.profile_patch)
        profile = self.profile_store.upsert_from_patch(request.user_id, effective_patch)
        history = self.chat_history.get_messages(request.session_id)

        safety_result = self.safety_checker.evaluate(request.message)
        if safety_result.is_unsafe:
            self.nutrition_clarifications.clear(request.session_id)
            self.chat_history.append_turn(
                request.session_id,
                request.user_id,
                user_message=request.message,
                assistant_message=safety_result.response or "",
            )
            return ChatResponse(
                session_id=request.session_id,
                reply=safety_result.response or "",
                intent="unsafe_medical_case",
                safety_flag=True,
                missing_fields=[],
                tool_results={},
            )

        pending_nutrition = self.nutrition_clarifications.get(request.session_id)
        if pending_nutrition:
            clarification_response = self._maybe_handle_pending_nutrition_clarification(
                request=request,
                pending_payload=pending_nutrition,
            )
            if clarification_response is not None:
                return clarification_response

        intent = self._detect_intent(request.message)
        if intent == "request_ingredient_calories":
            return self._handle_nutrition_request(request)

        missing_fields = self._collect_missing_fields(intent, profile)
        if missing_fields:
            reply = self.llm.generate_followup_question(intent=intent, missing_fields=missing_fields)
            self.chat_history.append_turn(
                request.session_id,
                request.user_id,
                user_message=request.message,
                assistant_message=reply,
            )
            return ChatResponse(
                session_id=request.session_id,
                reply=reply,
                intent=intent,
                safety_flag=False,
                missing_fields=missing_fields,
                tool_results={},
            )

        tool_results: dict[str, object] = {}
        if intent in {"request_tdee_macro", "request_meal_guidance"}:
            tool_results["tdee"] = calculate_tdee(profile)
            tool_results["macros"] = calculate_macros(profile)
        if intent == "request_workout_plan":
            tool_results["workout_plan"] = generate_workout_plan(profile)

        kb_context = []
        if intent in {"request_meal_guidance", "request_workout_plan"} or (
            intent == "general_fitness_qa" and self._should_use_general_kb(request.message)
        ):
            kb_context = self.retriever.retrieve(
                message=request.message,
                intent=intent,
                profile=profile,
            )

        prompt = {
            "system_prompt": build_system_prompt(intent),
            "profile_summary": build_profile_summary(profile),
            "personalization_summary": build_personalization_summary(profile),
            "profile_data": profile.model_dump(),
            "history": history,
            "message": request.message,
            "intent": intent,
            "tool_results": tool_results,
            "kb_context": kb_context,
        }
        reply = self.llm.generate(prompt)

        self.chat_history.append_turn(
            request.session_id,
            request.user_id,
            user_message=request.message,
            assistant_message=reply,
        )
        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            intent=intent,
            safety_flag=False,
            missing_fields=[],
            tool_results=tool_results,
        )

    def _detect_intent(self, message: str) -> str:
        lowered = normalize_text(message)

        if any(keyword in lowered for keyword in ["dau nguc", "kho tho", "ngat"]):
            return "unsafe_medical_case"
        if looks_like_nutrition_request(message):
            return "request_ingredient_calories"
        if any(keyword in lowered for keyword in ["tdee", "calo", "calories", "macro"]):
            return "request_tdee_macro"
        if any(keyword in lowered for keyword in ["lich an", "meal plan", "thuc don"]):
            return "request_meal_guidance"
        if any(keyword in lowered for keyword in ["lich tap", "workout", "giao an", "split"]):
            return "request_workout_plan"
        return "general_fitness_qa"

    def _should_use_general_kb(self, message: str) -> bool:
        lowered = normalize_text(message)
        fitness_keywords = [
            "tap",
            "workout",
            "gym",
            "cardio",
            "muscle",
            "protein",
            "macro",
            "calo",
            "calories",
            "meal",
            "thuc don",
            "lich an",
            "recovery",
            "hoi phuc",
            "progressive overload",
            "dau goi",
            "chan thuong",
            "tang co",
            "giam mo",
        ]
        return any(keyword in lowered for keyword in fitness_keywords)

    def _collect_missing_fields(self, intent: str, profile) -> list[str]:
        if intent == "request_workout_plan":
            required = ["goal", "workout_days_per_week", "train_location"]
        elif intent in {"request_tdee_macro", "request_meal_guidance"}:
            required = ["age", "sex", "height_cm", "weight_kg", "activity_level", "goal"]
        else:
            required = []

        missing: list[str] = []
        for field_name in required:
            if getattr(profile, field_name, None) in (None, "", []):
                missing.append(field_name)
        return missing

    def _maybe_handle_pending_nutrition_clarification(
        self,
        request: ChatRequest,
        pending_payload: dict[str, object],
    ) -> ChatResponse | None:
        if looks_like_nutrition_request(request.message):
            self.nutrition_clarifications.clear(request.session_id)
            return None

        if not self.nutrition_calculator.should_consume_pending_clarification(request.message):
            self.nutrition_clarifications.clear(request.session_id)
            return None

        result = self.nutrition_calculator.handle_pending_clarification(
            pending_payload=pending_payload,
            message=request.message,
        )
        self.nutrition_clarifications.clear(request.session_id)
        if result is None:
            return None

        return self._finalize_nutrition_result(
            request=request,
            result=result,
            original_message=str(pending_payload.get("original_message", request.message)),
        )

    def _handle_nutrition_request(self, request: ChatRequest) -> ChatResponse:
        result = self.nutrition_calculator.build_estimate(request.message)
        return self._finalize_nutrition_result(
            request=request,
            result=result,
            original_message=request.message,
        )

    def _finalize_nutrition_result(
        self,
        request: ChatRequest,
        result: dict[str, object],
        original_message: str,
    ) -> ChatResponse:
        tool_results = result.get("tool_results", {})
        if not isinstance(tool_results, dict):
            tool_results = {}

        if result.get("needs_clarification"):
            clarification_payload = result.get("clarification_payload", {})
            if isinstance(clarification_payload, dict) and clarification_payload:
                self.nutrition_clarifications.set(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    original_message=original_message,
                    payload=clarification_payload,
                )
        else:
            self.nutrition_clarifications.clear(request.session_id)
            self._augment_nutrition_result_with_llm_fallback(
                tool_results=tool_results,
                original_message=original_message,
            )

        reply = build_nutrition_reply(tool_results)

        self.chat_history.append_turn(
            request.session_id,
            request.user_id,
            user_message=request.message,
            assistant_message=reply,
        )
        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            intent="request_ingredient_calories",
            safety_flag=False,
            missing_fields=[],
            tool_results=tool_results,
        )

    def _augment_nutrition_result_with_llm_fallback(
        self,
        tool_results: dict[str, object],
        original_message: str,
    ) -> None:
        estimate = tool_results.get("nutrition_estimate", {})
        if not isinstance(estimate, dict):
            return

        unmatched_inputs = estimate.get("unmatched_inputs", [])
        if not isinstance(unmatched_inputs, list) or not unmatched_inputs:
            return

        llm_reply = self._generate_nutrition_llm_fallback(
            unmatched_inputs=unmatched_inputs,
            estimate=estimate,
            original_message=original_message,
        )
        if not llm_reply:
            llm_reply = self._build_generic_nutrition_fallback(unmatched_inputs)

        estimate["llm_fallback"] = {
            "source": "llm_estimate",
            "confidence": "low",
            "items": unmatched_inputs,
            "reply": llm_reply,
        }

    def _generate_nutrition_llm_fallback(
        self,
        unmatched_inputs: list[str],
        estimate: dict[str, object],
        original_message: str,
    ) -> str:
        fallback_prompt = {
            "intent": "nutrition_llm_fallback",
            "system_prompt": (
                "Ban la mot tro ly huu ich noi tieng Viet. "
                "Hay uoc luong so bo calories va macro cho nhung nguyen lieu hoac mon an chua co trong nutrition catalog. "
                "Day chi la uoc luong low-confidence, khong duoc trinh bay nhu con so chinh xac. "
                "Neu item mo ho, hay noi ro do la uoc luong tho va khuyen user nhap ten cu the hon hoac gram de tinh sat hon."
            ),
            "message": original_message,
            "history": [],
            "kb_context": [],
            "profile_summary": "",
            "personalization_summary": "",
            "profile_data": {},
            "tool_results": {},
            "nutrition_fallback_items": unmatched_inputs,
            "nutrition_known_totals": estimate.get("totals", {}),
        }
        try:
            reply = self.llm.generate(fallback_prompt).strip()
        except Exception:
            return ""
        return reply if self._looks_useful_nutrition_fallback(reply) else ""

    def _looks_useful_nutrition_fallback(self, reply: str) -> bool:
        normalized = normalize_text(reply)
        if len(normalized) < 24:
            return False
        forbidden_markers = [
            "tool_results",
            "response_rules",
            "intent:",
            "profile:",
            "history:",
            "knowledge context",
            "safety case",
            "channel|",
            "turn|",
        ]
        return not any(marker in normalized for marker in forbidden_markers)

    def _build_generic_nutrition_fallback(self, unmatched_inputs: list[str]) -> str:
        rendered_items = ", ".join(f"`{item}`" for item in unmatched_inputs)
        return (
            f"Phan {rendered_items} hien chua co trong nutrition catalog, nen minh chi co the uoc luong o muc low-confidence. "
            "Neu ban muon tinh sat hon, hay nhap ten cu the hon hoac tach thanh cac nguyen lieu chinh kem khoi luong theo gram."
        )
