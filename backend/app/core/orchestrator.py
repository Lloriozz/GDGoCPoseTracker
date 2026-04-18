from app.core.config import settings
from app.core.profile_extractor import extract_profile_patch_from_message, merge_profile_patches
from app.core.robust_text_utils import robust_normalize_text
from app.core.safety import SafetyChecker
from app.llm.factory import build_llm_backend
from app.memory.chat_history import ChatHistoryStore
from app.memory.nutrition_clarification_store import NutritionClarificationStore
from app.memory.profile_store import ProfileStore
from app.rag.retriever import KnowledgeRetriever
from app.rag.wiki_retriever import WikiKnowledgeRetriever
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse
from app.tools.nutrition_calculator import (
    NutritionCalculator,
    build_nutrition_reply,
    looks_like_nutrition_request,
)
from app.tools.macros import calculate_macros
from app.tools.tdee import calculate_tdee
from app.tools.workout_plan import generate_workout_plan


class FitnessChatOrchestrator:
    def __init__(self) -> None:
        self.profile_store = ProfileStore()
        self.chat_history = ChatHistoryStore(max_messages=settings.max_history_messages)
        self.nutrition_clarifications = NutritionClarificationStore()
        self.safety_checker = SafetyChecker()
        self.retriever = KnowledgeRetriever()
        self.wiki_retriever = WikiKnowledgeRetriever()
        self.nutrition_calculator = NutritionCalculator()
        self.llm = build_llm_backend()

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        inferred_patch = extract_profile_patch_from_message(request.message)
        effective_patch = merge_profile_patches(inferred_patch, request.profile_patch)
        profile = self.profile_store.upsert_from_patch(request.user_id, effective_patch)
        history = self.chat_history.get_messages(request.session_id)

        safety_result = self.safety_checker.evaluate(request.message)
        if safety_result.is_unsafe:
            return self._build_unsafe_medical_response(
                request=request,
                reply=safety_result.response or self._default_unsafe_medical_reply(),
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
        if intent == "unsafe_medical_case":
            return self._build_unsafe_medical_response(
                request=request,
                reply=safety_result.response or self._default_unsafe_medical_reply(),
            )
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

        tool_results = self._build_tool_results(intent=intent, profile=profile)
        domain_scope = self._classify_domain_scope(request.message, intent)

        kb_context = self._build_knowledge_context(
            message=request.message,
            intent=intent,
            profile=profile,
        )

        prompt = {
            "system_prompt": self._build_prompt_system(intent),
            "profile_summary": self._build_light_profile_summary(profile),
            "personalization_summary": self._build_personalization_summary(profile, intent),
            "profile_data": profile.model_dump(),
            "history": history[-3:],
            "message": request.message,
            "intent": intent,
            "domain_scope": domain_scope,
            "llm_route": self._build_llm_route(
                message=request.message,
                intent=intent,
                domain_scope=domain_scope,
                kb_context=kb_context,
            ),
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

    def _build_unsafe_medical_response(self, request: ChatRequest, reply: str) -> ChatResponse:
        self.nutrition_clarifications.clear(request.session_id)
        self.chat_history.append_turn(
            request.session_id,
            request.user_id,
            user_message=request.message,
            assistant_message=reply,
        )
        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            intent="unsafe_medical_case",
            safety_flag=True,
            missing_fields=[],
            tool_results={},
        )

    def _default_unsafe_medical_reply(self) -> str:
        return (
            "Minh khong nen tu van tap luyen tiep trong truong hop nay. "
            "Ban nen dung tap ngay va di kham hoac lien he nhan vien y te som, "
            "dac biet vi ban dang mo ta dau hieu can duoc danh gia truc tiep."
        )

    def _detect_intent(self, message: str) -> str:
        lowered = robust_normalize_text(message)

        if any(keyword in lowered for keyword in ["dau nguc", "kho tho", "ngat"]):
            return "unsafe_medical_case"
        if looks_like_nutrition_request(message):
            return "request_ingredient_calories"
        if any(
            keyword in lowered
            for keyword in [
                "tdee",
                "macro",
                "calories muc tieu",
                "calo muc tieu",
                "tinh calories",
                "tinh calo",
                "tinh macro",
            ]
        ):
            return "request_tdee_macro"
        if self._looks_like_workout_plan_request(lowered):
            return "request_workout_plan"
        if self._looks_like_meal_guidance_request(lowered):
            return "request_meal_guidance"
        return "general_fitness_qa"

    def _looks_like_workout_plan_request(self, lowered: str) -> bool:
        explicit_phrases = (
            "lap lich tap",
            "tao lich tap",
            "goi y lich tap",
            "workout plan",
            "chuong trinh tap",
            "plan tap",
        )
        return any(phrase in lowered for phrase in explicit_phrases)

    def _looks_like_meal_guidance_request(self, lowered: str) -> bool:
        explicit_phrases = (
            "goi y lich an",
            "lap lich an",
            "tao lich an",
            "goi y thuc don",
            "thuc don cho toi",
            "meal plan",
        )
        return any(phrase in lowered for phrase in explicit_phrases)

    def _classify_knowledge_topics(self, message: str, intent: str) -> set[str]:
        lowered = robust_normalize_text(message)
        topics: set[str] = set()

        meal_markers = [
            "an gi",
            "nen an gi",
            "mon gi",
            "thuc don",
            "meal",
            "bua",
            "pho",
            "bun",
            "com",
            "mon viet",
            "thay mon",
            "thay the",
            "tiet kiem",
            "chi phi",
            "bao nhieu tien",
            "het bao nhieu",
        ]
        nutrition_markers = [
            "dinh duong",
            "protein",
            "carb",
            "fat",
            "calo",
            "calories",
            "macro",
            "giam can",
            "giam mo",
            "tang co",
            "muscle gain",
            "fat loss",
        ]
        workout_markers = [
            "workout",
            "lich tap",
            "bai tap",
            "split",
            "progressive overload",
            "tap chan",
            "dau goi",
            "knee",
            "nen tranh gi",
            "tap sao",
        ]
        recovery_markers = [
            "recovery",
            "hoi phuc",
            "sau tap",
            "dien giai",
            "mat nuoc",
            "hydration",
            "deload",
            "doms",
            "dau co",
            "ngu",
            "tap xong",
            "moi tap xong",
        ]
        fasting_markers = [
            "fasting",
            "nhin an",
            "intermittent fasting",
            "an theo gio",
        ]

        if intent == "request_meal_guidance":
            topics.update({"meal", "nutrition"})
            if any(marker in lowered for marker in recovery_markers):
                topics.add("recovery")
            if any(marker in lowered for marker in fasting_markers):
                topics.add("fasting")
            return topics

        if intent == "request_workout_plan":
            topics.update({"workout", "recovery"})
            return topics

        if intent != "general_fitness_qa":
            return set()

        if any(marker in lowered for marker in meal_markers):
            topics.add("meal")
        if any(marker in lowered for marker in nutrition_markers):
            topics.add("nutrition")
        if any(marker in lowered for marker in workout_markers):
            topics.add("workout")
        if any(marker in lowered for marker in recovery_markers):
            topics.add("recovery")
        if any(marker in lowered for marker in fasting_markers):
            topics.add("fasting")

        return topics

    def _kb_category_prefixes_for_topics(self, topics: set[str]) -> tuple[str, ...]:
        prefixes: list[str] = []
        if {"meal", "nutrition"} & topics:
            prefixes.append("meal_")
        if "workout" in topics:
            prefixes.append("workout_")
        if "recovery" in topics:
            prefixes.append("recovery_")
        return tuple(dict.fromkeys(prefixes))

    def _wiki_sections_for_topics(self, topics: set[str]) -> set[str]:
        return {topic for topic in topics if topic in {"meal", "nutrition", "workout", "recovery", "fasting"}}

    def _build_knowledge_context(
        self,
        message: str,
        intent: str,
        profile,
    ) -> list[dict[str, object]]:
        if intent == "general_fitness_qa":
            topics = self._classify_knowledge_topics(message, intent)
            if not topics:
                return []

            base_context: list[dict[str, object]] = []
            wiki_context: list[dict[str, object]] = []
            kb_prefixes = self._kb_category_prefixes_for_topics(topics)
            wiki_sections = self._wiki_sections_for_topics(topics)

            if kb_prefixes:
                base_context = self.retriever.retrieve(
                    message=message,
                    intent=intent,
                    profile=profile,
                    allowed_category_prefixes=kb_prefixes,
                )

            if wiki_sections:
                wiki_context = self.wiki_retriever.retrieve(
                    message=message,
                    intent=intent,
                    profile=profile,
                    allowed_sections=wiki_sections,
                )

            return self._merge_knowledge_contexts(base_context, wiki_context)

        if intent not in {"request_meal_guidance", "request_workout_plan"}:
            return []

        topics = self._classify_knowledge_topics(message, intent)
        kb_prefixes = self._kb_category_prefixes_for_topics(topics)
        wiki_sections = self._wiki_sections_for_topics(topics)

        base_context = self.retriever.retrieve(
            message=message,
            intent=intent,
            profile=profile,
            allowed_category_prefixes=kb_prefixes or None,
        )
        wiki_context = self.wiki_retriever.retrieve(
            message=message,
            intent=intent,
            profile=profile,
            allowed_sections=wiki_sections or None,
        )
        return self._merge_knowledge_contexts(base_context, wiki_context)

    def _merge_knowledge_contexts(
        self,
        base_context: list[dict[str, object]],
        wiki_context: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        combined = [
            *[item for item in wiki_context if isinstance(item, dict)],
            *[item for item in base_context if isinstance(item, dict)],
        ]
        if not combined:
            return []

        def priority(item: dict[str, object]) -> tuple[int, float]:
            source = str(item.get("source", "kb"))
            page_type = str(item.get("page_type", ""))
            score = float(item.get("score", 0))
            if source == "wiki":
                if page_type == "concept":
                    return (6, score)
                if page_type in {"comparison", "entity"}:
                    return (5, score)
                if page_type == "index":
                    return (2, score)
                if page_type == "source-summary":
                    return (1, score)
            return (4, score)

        combined.sort(key=priority, reverse=True)
        unique_by_id: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        for item in combined:
            item_id = str(item.get("id", "")).strip()
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            unique_by_id.append(item)
            if len(unique_by_id) >= max(settings.rag_top_k, settings.wiki_top_k) + 1:
                break
        return unique_by_id

    def _collect_missing_fields(self, intent: str, profile) -> list[str]:
        if intent == "request_tdee_macro":
            required = ["age", "sex", "height_cm", "weight_kg", "activity_level", "goal"]
        elif intent == "request_meal_guidance":
            required = ["age", "sex", "height_cm", "weight_kg", "activity_level", "goal"]
        elif intent == "request_workout_plan":
            required = ["goal", "workout_days_per_week", "train_location"]
        else:
            required = []

        missing: list[str] = []
        for field_name in required:
            if getattr(profile, field_name, None) in (None, "", []):
                missing.append(field_name)
        return missing

    def _build_prompt_system(self, intent: str) -> str:
        if intent == "request_tdee_macro":
            return (
                "Ban la tro ly fitness noi tieng Viet. "
                "Hay bam sat so lieu da tinh san, giai thich ngan gon, va giu cau tra loi ro rang."
            )
        if intent in {"request_meal_guidance", "request_workout_plan"}:
            return (
                "Ban la tro ly fitness noi tieng Viet. "
                "Hay tong hop du lieu da co thanh goi y thuc te, ngan gon, va de ap dung."
            )
        return (
            "Ban la tro ly huu ich noi tieng Viet. "
            "Tra loi tu nhien, thuc te, va chi bam vao cau hoi hien tai. "
            "Neu co context lien quan thi tong hop bang loi cua ban thay vi liet ke noi bo."
        )

    def _build_light_profile_summary(self, profile) -> str:
        fields: list[str] = []

        if getattr(profile, "goal", None):
            fields.append(f"Muc tieu: {profile.goal}")
        if getattr(profile, "goal_detail", None):
            fields.append(f"Chi tiet muc tieu: {profile.goal_detail}")
        if getattr(profile, "activity_level", None):
            fields.append(f"Muc van dong: {profile.activity_level}")
        if getattr(profile, "workout_days_per_week", None) is not None:
            fields.append(f"So buoi tap/tuan: {profile.workout_days_per_week}")
        if getattr(profile, "train_location", None):
            fields.append(f"Noi tap: {profile.train_location}")
        if getattr(profile, "experience_level", None):
            fields.append(f"Kinh nghiem tap: {profile.experience_level}")
        if getattr(profile, "injuries", None):
            fields.append(f"Chan thuong: {', '.join(profile.injuries)}")
        if getattr(profile, "diet_preferences", None):
            fields.append(f"An uong: {', '.join(profile.diet_preferences)}")
        if getattr(profile, "allergies", None):
            fields.append(f"Di ung: {', '.join(profile.allergies)}")
        if getattr(profile, "budget_level", None):
            fields.append(f"Ngan sach: {profile.budget_level}")
        if getattr(profile, "cook_time_preference", None):
            fields.append(f"Thoi gian nau: {profile.cook_time_preference}")
        if getattr(profile, "preferred_foods", None):
            fields.append(f"Mon ua thich: {', '.join(profile.preferred_foods)}")
        if getattr(profile, "disliked_foods", None):
            fields.append(f"Mon khong thich: {', '.join(profile.disliked_foods)}")

        return "; ".join(fields)

    def _build_personalization_summary(self, profile, intent: str) -> str:
        notes: list[str] = []

        if getattr(profile, "goal_detail", None):
            notes.append(f"Chi tiet muc tieu: {profile.goal_detail}")

        if intent == "request_workout_plan":
            if getattr(profile, "experience_level", None):
                notes.append(f"Trinh do hien tai: {profile.experience_level}")
            if getattr(profile, "injuries", None):
                notes.append(f"Can tranh kich ung cho: {', '.join(profile.injuries)}")
        elif intent == "request_meal_guidance":
            if getattr(profile, "budget_level", None):
                notes.append(f"Ngan sach: {profile.budget_level}")
            if getattr(profile, "cook_time_preference", None):
                notes.append(f"Thoi gian nau: {profile.cook_time_preference}")
            if getattr(profile, "diet_preferences", None):
                notes.append(f"Cach an uu tien: {', '.join(profile.diet_preferences)}")
            if getattr(profile, "allergies", None):
                notes.append(f"Can tranh: {', '.join(profile.allergies)}")
            if getattr(profile, "preferred_foods", None):
                notes.append(f"Mon ua thich: {', '.join(profile.preferred_foods)}")
            if getattr(profile, "disliked_foods", None):
                notes.append(f"Mon khong thich: {', '.join(profile.disliked_foods)}")

        return "; ".join(notes)

    def _classify_domain_scope(self, message: str, intent: str) -> str:
        if intent != "general_fitness_qa":
            return "grounded"
        if self._classify_knowledge_topics(message, intent):
            return "fitness"
        return "out_of_domain"

    def _build_llm_route(
        self,
        *,
        message: str,
        intent: str,
        domain_scope: str,
        kb_context: list[dict[str, object]],
    ) -> dict[str, object]:
        if intent == "nutrition_llm_fallback":
            return {
                "mode": "nutrition_fallback",
                "prompt_style": "nutrition_fallback",
                "answer_brief": self._build_llm_answer_brief("nutrition_fallback"),
                "include_profile_context": False,
                "include_history_context": False,
                "include_kb_context": False,
            }

        if intent == "request_tdee_macro":
            return {
                "mode": "macro_summary",
                "prompt_style": "macro_summary",
                "answer_brief": self._build_llm_answer_brief("macro_summary"),
                "include_profile_context": True,
                "include_history_context": False,
                "include_kb_context": False,
            }

        if intent == "request_meal_guidance":
            return {
                "mode": "meal_guidance",
                "prompt_style": "grounded_guidance",
                "answer_brief": self._build_llm_answer_brief("meal_guidance"),
                "tool_context_label": "Neu da co khung so lieu lien quan, hay xem day la du lieu uu tien:",
                "closing_instruction": (
                    "Dua ra khung bua an goi y thuc te, uu tien mon de ap dung, "
                    "va chi nhac den calories/macro neu prompt co san so lieu ro rang."
                ),
                "include_profile_context": True,
                "include_history_context": True,
                "include_kb_context": True,
            }

        if intent == "request_workout_plan":
            return {
                "mode": "workout_guidance",
                "prompt_style": "grounded_guidance",
                "answer_brief": self._build_llm_answer_brief("workout_guidance"),
                "tool_context_label": "Neu da co mot khung lich tap tam thoi, hay xem day la boi canh uu tien:",
                "closing_instruction": (
                    "Dua ra lich tap hoac split goi y bang ngon ngu coach, "
                    "tap trung vao tinh thuc te va dieu chinh neu co chan thuong hay han che."
                ),
                "include_profile_context": True,
                "include_history_context": True,
                "include_kb_context": True,
            }

        general_mode = self._classify_general_llm_mode(
            message=message,
            domain_scope=domain_scope,
            kb_context=kb_context,
        )
        include_context = general_mode != "general_out_of_domain"
        return {
            "mode": general_mode,
            "prompt_style": "general_minimal",
            "answer_brief": "",
            "include_profile_context": include_context,
            "include_history_context": include_context,
            "include_kb_context": include_context,
        }

    def _build_llm_answer_brief(self, route_mode: str) -> str:
        briefs = {
            "macro_summary": "Tom tat ngan gon calories muc tieu va macro theo dung so trong du lieu.",
            "meal_guidance": (
                "Tao khung 3-5 bua an ro rang, moi bua co vi du mon ngan gon va de hieu, "
                "dua tren profile va knowledge context."
            ),
            "workout_guidance": (
                "Viet 1 doan ngan kieu coach, goi y split va cach sap buoi tap dua tren profile "
                "va knowledge context, khong can JSON."
            ),
            "nutrition_fallback": (
                "Uoc luong so bo cho tung muc chua co trong catalog, neu can thi dua ra khoang kcal "
                "thay vi mot con so cung. Noi ro day la uoc luong low-confidence."
            ),
        }
        return briefs.get(route_mode, "")

    def _classify_general_llm_mode(
        self,
        *,
        message: str,
        domain_scope: str,
        kb_context: list[dict[str, object]],
    ) -> str:
        if domain_scope == "out_of_domain":
            return "general_out_of_domain"

        lowered = robust_normalize_text(message)
        if self._looks_like_cost_question(lowered):
            return "general_cost_coaching"
        if self._looks_like_general_meal_question(lowered):
            return "general_meal_coaching"
        if self._looks_like_general_workout_question(lowered):
            return "general_workout_coaching"
        if self._looks_like_goal_coaching_question(lowered):
            return "general_goal_coaching"
        if self._looks_like_recovery_question(lowered):
            return "general_recovery_coaching"
        if kb_context:
            return "general_grounded_answer"
        return "general_default"

    def _looks_like_cost_question(self, lowered: str) -> bool:
        return any(marker in lowered for marker in ["bao nhieu tien", "chi phi", "het bao nhieu"])

    def _looks_like_general_meal_question(self, lowered: str) -> bool:
        meal_markers = [
            "nen an gi",
            "an gi",
            "mon viet",
            "protein",
            "tiet kiem",
            "lich an",
            "thuc don",
            "goi y mon",
        ]
        return any(marker in lowered for marker in meal_markers)

    def _looks_like_general_workout_question(self, lowered: str) -> bool:
        workout_markers = [
            "lich tap",
            "split",
            "tap chan",
            "dau goi",
            "co nen tap gym",
            "tap gym",
            "bai tap",
        ]
        return any(marker in lowered for marker in workout_markers)

    def _looks_like_goal_coaching_question(self, lowered: str) -> bool:
        return any(marker in lowered for marker in ["giam can", "giam mo", "fat loss"])

    def _looks_like_recovery_question(self, lowered: str) -> bool:
        return any(marker in lowered for marker in ["dien giai", "bu nuoc", "hydration", "sau tap"])

    def _build_tool_results(self, intent: str, profile) -> dict[str, object]:
        tool_results: dict[str, object] = {}

        if intent in {"request_tdee_macro", "request_meal_guidance"}:
            tdee = calculate_tdee(profile)
            macros = calculate_macros(profile)
            if tdee:
                tool_results["tdee"] = tdee
            if macros:
                tool_results["macros"] = macros

        if intent == "request_workout_plan":
            workout_plan = generate_workout_plan(profile)
            if workout_plan:
                tool_results["workout_plan"] = workout_plan

        if intent == "request_meal_guidance":
            macros = tool_results.get("macros", {})
            if isinstance(macros, dict) and macros:
                tool_results["meal_plan"] = self._build_meal_plan_scaffold(profile, macros)

        return tool_results

    def _build_meal_plan_scaffold(self, profile, macros: dict[str, object]) -> dict[str, object]:
        target_calories = int(macros.get("target_calories", 0) or 0)
        protein_g = int(macros.get("protein_g", 0) or 0)
        carb_g = int(macros.get("carb_g", 0) or 0)
        fat_g = int(macros.get("fat_g", 0) or 0)
        examples = self._build_meal_examples_from_profile(profile)
        ratios = [
            ("Bua sang", 0.25, 0.25, 0.25, 0.25, examples[0]),
            ("Bua trua", 0.30, 0.30, 0.30, 0.30, examples[1]),
            ("Bua phu", 0.15, 0.15, 0.15, 0.15, examples[2]),
            ("Bua toi", 0.30, 0.30, 0.30, 0.30, examples[3]),
        ]

        remaining = {
            "calories": target_calories,
            "protein_g": protein_g,
            "carb_g": carb_g,
            "fat_g": fat_g,
        }
        meals: list[dict[str, object]] = []
        for index, (name, cal_ratio, protein_ratio, carb_ratio, fat_ratio, example) in enumerate(ratios):
            is_last = index == len(ratios) - 1
            if is_last:
                meal = {
                    "name": name,
                    "calories": remaining["calories"],
                    "protein_g": remaining["protein_g"],
                    "carb_g": remaining["carb_g"],
                    "fat_g": remaining["fat_g"],
                    "example": example,
                }
            else:
                calories = round(target_calories * cal_ratio)
                protein = round(protein_g * protein_ratio)
                carbs = round(carb_g * carb_ratio)
                fat = round(fat_g * fat_ratio)
                meal = {
                    "name": name,
                    "calories": calories,
                    "protein_g": protein,
                    "carb_g": carbs,
                    "fat_g": fat,
                    "example": example,
                }
                remaining["calories"] -= calories
                remaining["protein_g"] -= protein
                remaining["carb_g"] -= carbs
                remaining["fat_g"] -= fat
            meals.append(meal)

        notes: list[str] = []
        if getattr(profile, "budget_level", None) == "low":
            notes.append("Uu tien mon de mua va de prep de bam ngan sach.")
        if getattr(profile, "cook_time_preference", None) == "quick":
            notes.append("Uu tien bua co the chuan bi nhanh trong 10-15 phut.")
        if getattr(profile, "diet_preferences", None):
            notes.append(f"Luu y cach an: {', '.join(profile.diet_preferences)}")
        if getattr(profile, "allergies", None):
            notes.append(f"Can tranh thanh phan: {', '.join(profile.allergies)}")

        return {
            "target_calories": target_calories,
            "protein_g": protein_g,
            "carb_g": carb_g,
            "fat_g": fat_g,
            "meals": meals,
            "notes": notes,
        }

    def _build_meal_examples_from_profile(self, profile) -> list[str]:
        normalized_preferences = {
            robust_normalize_text(str(item)) for item in getattr(profile, "diet_preferences", []) or []
        }
        normalized_allergies = {
            robust_normalize_text(str(item)) for item in getattr(profile, "allergies", []) or []
        }
        preferred_foods = [str(item) for item in getattr(profile, "preferred_foods", []) or []]
        disliked_foods = {
            robust_normalize_text(str(item)) for item in getattr(profile, "disliked_foods", []) or []
        }

        if {"vegetarian", "an chay", "vegan"} & normalized_preferences:
            defaults = [
                "yen mach + sua dau nanh + chuoi",
                "com + dau hu + rau",
                "edamame + khoai + trai cay",
                "banh mi nguyen cam + dau hu + salad",
            ]
        else:
            defaults = [
                "yen mach + sua chua + chuoi + whey",
                "com + uc ga + rau + trai cay",
                "banh mi nguyen cam + trung",
                "com hoac khoai + bo nac hoac ca + rau",
            ]

        if {"milk", "sua", "dairy", "lactose"} & normalized_allergies:
            defaults = [
                item.replace("sua chua", "sua dau nanh").replace(" + whey", " + protein thuc vat")
                for item in defaults
            ]

        preferred_examples: list[str] = []
        for item in preferred_foods:
            normalized = robust_normalize_text(item)
            if "pho" in normalized:
                preferred_examples.append("pho ga it mo + trai cay")
            elif "trung" in normalized:
                preferred_examples.append("trung + banh mi nguyen cam + trai cay")
            elif "bun" in normalized:
                preferred_examples.append("bun ga xe + rau")
            elif "com" in normalized:
                preferred_examples.append("com + uc ga + rau")
            elif "dau hu" in normalized or "tofu" in normalized:
                preferred_examples.append("dau hu ap chao + com + rau")

        selected: list[str] = []
        seen: set[str] = set()
        for candidate in [*preferred_examples, *defaults]:
            normalized_candidate = robust_normalize_text(candidate)
            if not candidate or normalized_candidate in seen:
                continue
            if any(disliked in normalized_candidate for disliked in disliked_foods if disliked):
                continue
            seen.add(normalized_candidate)
            selected.append(candidate)
            if len(selected) == 4:
                break

        while len(selected) < 4:
            selected.append(defaults[len(selected)])
        return selected

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
            ),
            "message": original_message,
            "history": [],
            "kb_context": [],
            "profile_summary": "",
            "personalization_summary": "",
            "profile_data": {},
            "domain_scope": "grounded",
            "llm_route": self._build_llm_route(
                message=original_message,
                intent="nutrition_llm_fallback",
                domain_scope="grounded",
                kb_context=[],
            ),
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
        normalized = robust_normalize_text(reply)
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
