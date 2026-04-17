from app.core.robust_text_utils import repair_mojibake, robust_normalize_text
from app.llm.base import BaseLLMBackend


class MockGemmaInferencer(BaseLLMBackend):
    def generate(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", "general_fitness_qa"))
        tool_results = prompt.get("tool_results", {})
        profile_data = prompt.get("profile_data", {})
        kb_context = prompt.get("kb_context", [])
        message = str(prompt.get("message", ""))
        normalized_message = robust_normalize_text(message)
        nutrition_fallback_items = prompt.get("nutrition_fallback_items", [])

        if intent == "nutrition_llm_fallback" and isinstance(nutrition_fallback_items, list):
            return self._build_nutrition_fallback_reply(nutrition_fallback_items)

        if intent == "request_workout_plan":
            workout_plan = tool_results.get("workout_plan", {})
            if isinstance(workout_plan, dict) and workout_plan:
                return self._build_workout_reply(workout_plan, profile_data, kb_context)
            return self._build_wiki_workout_guidance(profile_data, kb_context)

        if intent == "request_meal_guidance":
            macros = tool_results.get("macros", {})
            if isinstance(macros, dict) and macros:
                return self._generate_meal_guidance(macros, profile_data, kb_context)
            return self._build_wiki_meal_guidance(profile_data, kb_context)

        if intent == "request_tdee_macro":
            macros = tool_results.get("macros", {})
            if isinstance(macros, dict) and macros:
                return (
                    f"Mức calories mục tiêu của bạn hiện là {macros.get('target_calories')} kcal/ngày, "
                    f"với {macros.get('protein_g')}g protein, {macros.get('fat_g')}g fat và {macros.get('carb_g')}g carb. "
                    "Đây là khung rất tốt để đi tiếp sang meal plan."
                )

        if any(keyword in normalized_message for keyword in ["bao nhieu tien", "chi phi", "het bao nhieu"]):
            return self._build_cost_reply(profile_data)

        if intent == "general_fitness_qa":
            return self._build_general_fitness_reply(message, profile_data, kb_context)

        return self._build_general_reply(message)

    def _build_workout_reply(
        self,
        workout_plan: dict[str, object],
        profile_data: object,
        kb_context: object,
    ) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        split = workout_plan.get("split", "custom")
        days = workout_plan.get("days", [])
        experience_level = profile_data.get("experience_level")
        goal_detail = repair_mojibake(str(profile_data.get("goal_detail", "")).strip())

        segments = [f"Mình đã lên khung lịch tập theo split {split} với {len(days)} buổi"]
        if experience_level:
            segments.append(f"và mình đang giữ độ khó hợp hơn với trình độ {experience_level}")
        if goal_detail:
            segments.append(f"đồng thời vẫn bám theo ưu tiên của bạn là {goal_detail}")

        knowledge_note = self._build_workout_kb_note(kb_context)
        reply = (
            ", ".join(segments)
            + ". Bạn có thể dùng lịch này làm bản nháp rồi tối ưu thêm theo feedback thực tế."
        )
        if knowledge_note:
            reply += f" {knowledge_note}"
        return reply

    def _build_wiki_workout_guidance(
        self,
        profile_data: object,
        kb_context: object,
    ) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        workout_days = int(profile_data.get("workout_days_per_week") or 3)
        split = self._suggest_split_name(workout_days)
        display_split = split.replace("_", "/")
        experience_level = str(profile_data.get("experience_level", "")).strip()
        goal_detail = repair_mojibake(str(profile_data.get("goal_detail", "")).strip())
        train_location = str(profile_data.get("train_location", "")).strip()
        normalized_injuries = {
            robust_normalize_text(str(item)) for item in profile_data.get("injuries") or []
        }
        knee_sensitive = bool({"knee", "goi", "dau goi"} & normalized_injuries)
        shoulder_sensitive = bool({"shoulder", "vai", "dau vai"} & normalized_injuries)

        opening = [f"Voi {workout_days} buoi moi tuan, minh nghieng ve split {display_split} de de bam va de tang tai."]
        if experience_level:
            opening.append(f"Muc do hien tai se hop hon voi trinh do {experience_level}.")
        if train_location:
            opening.append(f"Minh uu tien bai tap hop voi boi canh tap o {train_location}.")
        if goal_detail:
            opening.append(f"Uu tien rieng can nho la: {goal_detail}.")

        day_lines = [f"- Buoi {index + 1}: {focus}" for index, focus in enumerate(self._build_day_focuses(split, workout_days))]

        notes: list[str] = []
        if knee_sensitive:
            notes.append(
                "Neu dau goi nhay cam, uu tien ROM kiem soat, hip hinge, box squat hoac leg press nhe, "
                "va tranh nhoi volume squat/lunge qua cao."
            )
        if shoulder_sensitive:
            notes.append(
                "Neu vai nhay cam, uu tien may on dinh, giam overhead volume, va tang bai keo/face pull de giu vai on dinh."
            )
        knowledge_note = self._build_workout_kb_note(kb_context)
        if knowledge_note:
            notes.append(knowledge_note)

        sections = [" ".join(opening), "\n".join(day_lines)]
        if notes:
            sections.append(" ".join(notes))
        return "\n".join(section for section in sections if section)

    def _build_wiki_meal_guidance(
        self,
        profile_data: object,
        kb_context: object,
    ) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        goal = str(profile_data.get("goal", "")).strip()
        if goal == "muscle_gain":
            opening = "Minh goi y khung an uu tien phuc hoi va giu protein on dinh de de bam muc tieu tang co."
        elif goal == "fat_loss":
            opening = "Minh goi y khung an uu tien no lau, de ap dung, va giu protein on dinh de ho tro giam mo."
        else:
            opening = "Minh goi y mot khung an thuc te, de xoay tua hang ngay va de dieu chinh theo muc tieu cua ban."

        meal_examples = self._build_meal_examples(profile_data, kb_context)
        meal_names = ["Bua sang", "Bua trua", "Bua phu", "Bua toi"]
        meal_lines = [
            f"- {meal_name}: {example}"
            for meal_name, example in zip(meal_names, meal_examples, strict=False)
        ]

        notes = [note for note in [self._build_preference_note(profile_data), self._build_kb_note(kb_context)] if note]
        sections = [opening, "\n".join(meal_lines)]
        if notes:
            sections.append(" ".join(notes))
        return "\n".join(section for section in sections if section)

    def _generate_meal_guidance(
        self,
        macros: dict[str, object],
        profile_data: object,
        kb_context: object,
    ) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        target_calories = int(macros.get("target_calories", 0))
        protein_g = int(macros.get("protein_g", 0))
        fat_g = int(macros.get("fat_g", 0))
        carb_g = int(macros.get("carb_g", 0))

        meal_examples = self._build_meal_examples(profile_data, kb_context)
        meals = self._build_meal_targets(
            target_calories,
            protein_g,
            fat_g,
            carb_g,
            meal_examples,
        )
        meal_lines = [
            (
                f"- {meal['name']}: ~{meal['calories']} kcal, "
                f"{meal['protein_g']}g protein, {meal['carb_g']}g carb, {meal['fat_g']}g fat. "
                f"Gợi ý: {meal['example']}"
            )
            for meal in meals
        ]

        preference_note = self._build_preference_note(profile_data)
        knowledge_note = self._build_kb_note(kb_context)
        summary = (
            f"Khung ăn uống gợi ý cho mức {target_calories} kcal/ngày "
            f"({protein_g}g protein, {fat_g}g fat, {carb_g}g carb):"
        )
        body = "\n".join(meal_lines)

        notes = [note for note in [preference_note, knowledge_note] if note]
        if notes:
            return f"{summary}\n{body}\n{' '.join(notes)}"
        return f"{summary}\n{body}"

    def _build_meal_targets(
        self,
        target_calories: int,
        protein_g: int,
        fat_g: int,
        carb_g: int,
        meal_examples: list[str] | None = None,
    ) -> list[dict[str, object]]:
        examples = meal_examples or [
            "yến mạch + sữa chua Hy Lạp + chuối + whey",
            "cơm + ức gà/áp chảo + rau + trái cây",
            "bánh mì nguyên cám + trứng + sữa",
            "cơm/khoai + bò nạc/cá + rau + sữa chua",
        ]
        ratios = [
            ("Bữa sáng", 0.25, 0.25, 0.25, 0.25, examples[0]),
            ("Bữa trưa", 0.3, 0.3, 0.3, 0.3, examples[1]),
            ("Bữa phụ", 0.15, 0.15, 0.15, 0.15, examples[2]),
            ("Bữa tối", 0.3, 0.3, 0.3, 0.3, examples[3]),
        ]

        meals: list[dict[str, object]] = []
        remaining = {
            "calories": target_calories,
            "protein_g": protein_g,
            "carb_g": carb_g,
            "fat_g": fat_g,
        }

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

        return meals

    def _build_preference_note(self, profile_data: dict[str, object]) -> str:
        diet_preferences = profile_data.get("diet_preferences") or []
        allergies = profile_data.get("allergies") or []
        preferred_foods = profile_data.get("preferred_foods") or []
        disliked_foods = profile_data.get("disliked_foods") or []
        budget_level = profile_data.get("budget_level")
        cook_time_preference = profile_data.get("cook_time_preference")

        notes: list[str] = []
        if diet_preferences:
            notes.append(f"Lưu ý ưu tiên cách ăn: {', '.join(str(item) for item in diet_preferences)}.")
        if allergies:
            notes.append(f"Cần tránh các món liên quan đến: {', '.join(str(item) for item in allergies)}.")
        if preferred_foods:
            notes.append(
                f"Nếu hợp khẩu vị và mục tiêu, có thể ưu tiên xoay tua các món bạn thích như: {', '.join(str(item) for item in preferred_foods)}."
            )
        if disliked_foods:
            notes.append(f"Nên hạn chế các món bạn không thích như: {', '.join(str(item) for item in disliked_foods)}.")
        if budget_level == "low":
            notes.append("Nếu cần tiết kiệm, ưu tiên trứng, đậu hũ, ức gà, sữa chua, yến mạch và cơm trắng.")
        elif budget_level == "high":
            notes.append("Nếu ngân sách thoải mái hơn, có thể thêm cá hồi, bò nạc, quả mọng và sữa chua Hy Lạp.")
        if cook_time_preference == "quick":
            notes.append("Ưu tiên món nấu nhanh hoặc prep sẵn trong 10-15 phút để dễ bám kế hoạch hơn.")

        if notes:
            return " ".join(notes)
        return ""

    def _build_meal_examples(
        self,
        profile_data: dict[str, object],
        kb_context: object,
    ) -> list[str]:
        normalized_preferences = {
            robust_normalize_text(str(item)) for item in profile_data.get("diet_preferences") or []
        }
        normalized_allergies = {
            robust_normalize_text(str(item)) for item in profile_data.get("allergies") or []
        }
        preferred_foods = [str(item) for item in profile_data.get("preferred_foods") or []]
        disliked_foods = {
            robust_normalize_text(str(item)) for item in profile_data.get("disliked_foods") or []
        }

        if {"vegetarian", "an chay", "vegan"} & normalized_preferences:
            defaults = [
                "yến mạch + sữa đậu nành + chuối",
                "cơm + đậu hũ áp chảo + rau",
                "edamame + khoai + trái cây",
                "bánh mì nguyên cám + tempeh/đậu hũ + salad",
            ]
        else:
            defaults = [
                "yến mạch + sữa chua Hy Lạp + chuối + whey",
                "cơm + ức gà/áp chảo + rau + trái cây",
                "bánh mì nguyên cám + trứng + sữa",
                "cơm/khoai + bò nạc/cá + rau + sữa chua",
            ]

        if {"milk", "sua", "dairy", "lactose"} & normalized_allergies:
            defaults = [
                item.replace("sữa chua Hy Lạp", "sữa đậu nành không đường")
                .replace("whey", "protein thực vật")
                .replace(" + sữa", "")
                .replace(" + sữa chua", "")
                for item in defaults
            ]

        kb_examples: list[str] = []
        if isinstance(kb_context, list):
            for item in kb_context:
                if not isinstance(item, dict):
                    continue
                category = str(item.get("category", ""))
                if category not in {
                    "meal_budget",
                    "meal_quick",
                    "meal_substitution",
                    "meal_vietnamese",
                    "meal_constraint_vegetarian",
                    "meal_constraint_dairy_free",
                }:
                    continue
                examples = item.get("examples", [])
                if not isinstance(examples, list):
                    continue
                kb_examples.extend(str(example) for example in examples)

        preferred_examples = []
        for item in preferred_foods:
            normalized = robust_normalize_text(item)
            if "pho" in normalized:
                preferred_examples.append("phở bò ít mỡ + trái cây")
            elif "trung" in normalized:
                preferred_examples.append("trứng + bánh mì nguyên cám + trái cây")
            elif "bun" in normalized:
                preferred_examples.append("bún gà xé + rau")
            elif "com" in normalized:
                preferred_examples.append("cơm + ức gà + rau")
            elif "dau hu" in normalized or "tofu" in normalized:
                preferred_examples.append("đậu hũ áp chảo + cơm + rau")

        ordered_candidates = preferred_examples + kb_examples + defaults
        seen: set[str] = set()
        selected: list[str] = []
        for candidate in ordered_candidates:
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

    def _suggest_split_name(self, workout_days: int) -> str:
        if workout_days <= 3:
            return "full_body"
        if workout_days == 4:
            return "upper_lower"
        return "push_pull_legs"

    def _build_day_focuses(self, split: str, workout_days: int) -> list[str]:
        if split == "full_body":
            templates = [
                "Full body A, ưu tiên động tác cơ bản và kỹ thuật ổn.",
                "Full body B, nhấn vào kéo-đẩy cân bằng và thân giữa.",
                "Full body C, lặp lại mẫu chuyển động với biến thể nhẹ hơn.",
            ]
            return templates[:workout_days]
        if split == "upper_lower":
            templates = [
                "Upper 1, ưu tiên press + row + vai + tay sau tay trước.",
                "Lower 1, ưu tiên hip hinge, squat biến thể và core.",
                "Upper 2, lặp lại thân trên với góc bài tập khác một chút.",
                "Lower 2, nhấn vào chân sau, mông và bài một chân có kiểm soát.",
            ]
            return templates[:workout_days]
        templates = [
            "Push, ưu tiên ngực vai tay sau.",
            "Pull, ưu tiên lưng xô, rear delt và tay trước.",
            "Legs, ưu tiên chân trước, chân sau, mông và core.",
            "Upper, lặp lại thân trên theo mức vừa phải.",
            "Lower, lặp lại thân dưới theo mức vừa phải.",
        ]
        return templates[:workout_days]

    def _build_cost_reply(self, profile_data: object) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        budget_level = profile_data.get("budget_level")
        cook_time_preference = profile_data.get("cook_time_preference")

        if budget_level == "low":
            reply = (
                "Với mức ngân sách tiết kiệm, mình sẽ ưu tiên các món như trứng, đậu hũ, ức gà, sữa chua và cơm "
                "để giữ chi phí mỗi ngày thấp hơn mà vẫn dễ bám macro."
            )
        elif budget_level == "high":
            reply = (
                "Nếu ngân sách thoải mái hơn, bạn có thể dùng các lựa chọn như bò nạc, cá hồi, sữa chua Hy Lạp "
                "và trái cây đa dạng hơn, nên chi phí mỗi ngày cũng sẽ cao hơn."
            )
        else:
            reply = (
                "Chi phí mỗi ngày còn phụ thuộc vào loại thực phẩm, khẩu phần và nơi bạn mua đồ ăn, nhưng mình có "
                "thể ước tính theo mức tiết kiệm, vừa phải hoặc thoải mái để bạn dễ hình dung."
            )

        if cook_time_preference == "quick":
            reply += " Nếu bạn muốn nấu nhanh, mình cũng sẽ ưu tiên các món prep gọn để giảm cả thời gian lẫn chi phí phát sinh."

        reply += " Nếu muốn, mình có thể chuyển luôn khung ăn hiện tại thành bản ước tính chi phí theo ngày."
        return reply

    def _build_kb_note(self, kb_context: object) -> str:
        ranked_items = self._rank_kb_context_items(kb_context)
        if not ranked_items:
            return ""

        notes: list[str] = []
        for item in ranked_items[:2]:
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            first_sentence = content.split(".")[0].strip()
            if title and first_sentence:
                notes.append(f"{title}: {first_sentence}.")
        if not notes:
            return ""
        return "Bạn có thể tham khảo thêm: " + " ".join(notes)

    def _build_workout_kb_note(self, kb_context: object) -> str:
        ranked_items = self._rank_kb_context_items(kb_context)
        if not ranked_items:
            return ""

        for item in ranked_items:
            category = str(item.get("category", ""))
            if not category.startswith(("workout", "recovery")):
                continue
            content = str(item.get("content", "")).strip()
            first_sentence = content.split(".")[0].strip()
            if first_sentence:
                return f"Gợi ý thêm: {first_sentence}."
        return ""

    def _answer_from_kb(self, kb_context: list[object]) -> str:
        usable_entries = self._rank_kb_context_items(kb_context)
        if not usable_entries:
            return self._build_general_reply("")

        segments: list[str] = []
        for entry in usable_entries[:3]:
            title = str(entry.get("title", "")).strip()
            content = str(entry.get("content", "")).strip()
            first_sentence = content.split(".")[0].strip()
            if first_sentence:
                if title:
                    segments.append(f"- {title}: {first_sentence}.")
                else:
                    segments.append(f"- {first_sentence}.")

        if segments:
            return "Minh goi y ngan gon nhu sau:\n" + "\n".join(segments)

        return (
            self._build_general_reply("")
        )

    def _rank_kb_context_items(self, kb_context: object) -> list[dict[str, object]]:
        if not isinstance(kb_context, list):
            return []

        usable_entries = [item for item in kb_context if isinstance(item, dict)]
        if not usable_entries:
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

        usable_entries.sort(key=priority, reverse=True)
        return usable_entries

    def _build_general_fitness_reply(
        self,
        message: str,
        profile_data: object,
        kb_context: object,
    ) -> str:
        normalized_message = robust_normalize_text(message)

        if any(
            marker in normalized_message
            for marker in ["nen an gi", "an gi", "mon viet", "protein", "tiet kiem", "lich an", "thuc don", "goi y mon"]
        ):
            return self._build_general_meal_reply(profile_data, kb_context, normalized_message)

        if any(
            marker in normalized_message
            for marker in ["lich tap", "split", "tap chan", "dau goi", "co nen tap gym", "tap gym", "bai tap"]
        ):
            return self._build_general_workout_reply(profile_data, kb_context, normalized_message)

        if any(marker in normalized_message for marker in ["giam can", "giam mo", "fat loss"]):
            kb_note = self._build_kb_note(kb_context)
            reply = (
                "De giam can ben vung, ban nen giu tham hut calo vua phai, uu tien protein on dinh, "
                "an cac bua de bam lau va tap deu trong vai tuan de theo doi tien do."
            )
            return f"{reply} {kb_note}".strip() if kb_note else reply

        if any(marker in normalized_message for marker in ["dien giai", "bu nuoc", "hydration", "sau tap"]):
            kb_note = self._build_kb_note(kb_context)
            reply = (
                "Dien giai quan trong hon khi ban do mo hoi nhieu, tap lau hoac tap trong moi truong nong. "
                "Neu buoi tap nhe va ban an uong binh thuong, uu tien bu nuoc va an lai mot bua hop ly la du."
            )
            return f"{reply} {kb_note}".strip() if kb_note else reply

        if isinstance(kb_context, list) and kb_context:
            return self._answer_from_kb(kb_context)

        return self._build_general_reply(message)

    def _build_general_reply(self, message: str) -> str:
        cleaned_message = " ".join(repair_mojibake(message).strip().split())
        normalized_message = robust_normalize_text(cleaned_message)

        if any(marker in normalized_message for marker in ["tai khoan ngan hang", "mo tai khoan", "ngan hang"]):
            return (
                "Ban co the bat dau bang cach chon ngan hang, chuan bi CCCD hoac giay to tuy than, "
                "roi dang ky tren app hoac ra chi nhanh de xac thuc thong tin theo huong dan cua ngan hang do."
            )

        if cleaned_message:
            return (
                f"Voi cau hoi \"{cleaned_message}\", minh se uu tien tra loi gon va thuc te nhat theo thong tin hien co. "
                "Neu ban muon, minh co the di sau hon vao mot muc tieu cu the hon o turn tiep theo."
            )
        return (
            "Minh co the giup ban tra loi ngan gon va thuc te hon neu ban noi ro hon dieu ban muon hoi."
        )

    def _build_general_meal_reply(
        self,
        profile_data: object,
        kb_context: object,
        normalized_message: str,
    ) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        normalized_preferences = {
            robust_normalize_text(str(item)) for item in profile_data.get("diet_preferences") or []
        }
        normalized_allergies = {
            robust_normalize_text(str(item)) for item in profile_data.get("allergies") or []
        }

        if any(marker in normalized_message for marker in ["sau tap", "tap xong", "moi tap xong"]):
            base = (
                "Sau tap, ban nen uu tien mot bua co protein ro rang kem carb de hoi phuc tot hon, "
                "vi du com + uc ga, bun + trung, hoac sua chua + chuoi neu can gon nhe."
            )
        elif any(marker in normalized_message for marker in ["giam can", "giam mo", "fat loss"]):
            base = (
                "Neu dang giam can, ban nen uu tien bua co protein ro rang, rau de no lau, "
                "va giu phan carb vua du, vi du uc ga + rau + com it hon, trung + salad + khoai, hoac dau hu + rau + com."
            )
        elif any(marker in normalized_message for marker in ["tang co", "muscle gain"]):
            base = (
                "Neu uu tien tang co, hay giu moi bua co protein ro rang kem carb de hoi phuc va tap tot hon, "
                "vi du com + uc ga, bun + bo nac, pho ga it mo, hoac sua chua + chuoi + yen mach."
            )
        elif {"vegetarian", "an chay", "vegan"} & normalized_preferences:
            base = (
                "Neu ban an chay, hay uu tien dau hu, edamame, sua dau nanh, sua chua thuc vat va cac bua com hoac bun co them rau "
                "de giu du protein ma van de bam hang ngay."
            )
        elif "tiet kiem" in normalized_message and "protein" in normalized_message:
            base = (
                "Neu muon tiet kiem ma van du protein, ban co the uu tien trung, dau hu, uc ga, ca hop, "
                "sua chua va com hoac khoai de de xoay tua hang ngay."
            )
        else:
            base = (
                "Ban co the di theo huong moi bua co protein ro rang, them rau, va chon carb vua du theo muc tieu. "
                "Cac mon de bam nhat thuong la com + thit nac, bun + trung, pho ga it mo, hoac dau hu + com + rau."
            )

        if {"milk", "sua", "dairy", "lactose"} & normalized_allergies:
            base += " Neu khong hop sua, co the doi sang sua dau nanh khong duong hoac protein thuc vat."

        kb_note = self._build_kb_note(kb_context)
        return f"{base} {kb_note}".strip() if kb_note else base

    def _build_general_workout_reply(
        self,
        profile_data: object,
        kb_context: object,
        normalized_message: str,
    ) -> str:
        if not isinstance(profile_data, dict):
            profile_data = {}

        if "dau goi" in normalized_message:
            base = (
                "Neu dau goi nhay cam, uu tien cac bai kiem soat ROM, tang tai tu tu, "
                "va tranh nhoi squat hoac lunge qua cao khi dang bi kich ung."
            )
        elif "co nen tap gym" in normalized_message or "tap gym khong" in normalized_message:
            base = (
                "Neu suc khoe hien tai on va ban muon cai thien the luc, tap gym la mot lua chon rat on "
                "mien la ban bat dau voi muc vua phai, hoc ky thuat tu tu, va duy tri deu."
            )
        elif profile_data.get("workout_days_per_week") == 4 or "4 buoi" in normalized_message:
            base = (
                "Neu ban tap 4 buoi moi tuan, split upper/lower thuong la mot diem bat dau rat de bam "
                "vi vua de lap lai, vua de theo doi tien do."
            )
        else:
            base = (
                "Ban nen bat dau voi mot lich de bam, uu tien ky thuat on va tang tai tu tu thay vi doi hoi lich qua phuc tap ngay tu dau."
            )

        kb_note = self._build_workout_kb_note(kb_context)
        return f"{base} {kb_note}".strip() if kb_note else base

    def _build_nutrition_fallback_reply(self, items: list[object]) -> str:
        lines = [
            "Cac muc duoi day chua co trong nutrition catalog, nen minh chi uoc luong o muc low-confidence:"
        ]
        for item in items:
            raw_item = str(item).strip()
            normalized_item = robust_normalize_text(raw_item)
            if "rong bien" in normalized_item:
                lines.append(
                    f"- `{raw_item}`: neu la rong bien an kem hoac rong bien kho thong thuong thi calories thuong khong cao, "
                    "nhung neu la loai say gion, tam vi hoac co them dau/duong thi so co the chenh kha nhieu."
                )
            elif "pho" in normalized_item:
                lines.append(
                    f"- `{raw_item}`: neu la mot to pho pho bien thi thuong nam trong khoang 450-700 kcal, "
                    "nhung con so nay phu thuoc kha manh vao luong banh pho, thit va mo nuoc dung."
                )
            else:
                lines.append(
                    f"- `{raw_item}`: minh chua co du lieu chuan cho muc nay, nen tam thoi chi co the dua ra uoc luong tho va khong nen xem nhu con so chinh xac."
                )

        lines.append(
            "Neu ban muon tinh sat hon, hay nhap ten cu the hon hoac tach thanh nguyen lieu chinh kem khoi luong theo gram."
        )
        return "\n".join(lines)
