from abc import ABC, abstractmethod
import json


class BaseLLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt: dict[str, object]) -> str:
        raise NotImplementedError

    def generate_followup_question(self, intent: str, missing_fields: list[str]) -> str:
        labels = {
            "age": "tuổi",
            "sex": "giới tính",
            "height_cm": "chiều cao",
            "weight_kg": "cân nặng",
            "goal": "mục tiêu",
            "goal_detail": "chi tiết mục tiêu",
            "activity_level": "mức vận động hằng ngày",
            "workout_days_per_week": "số buổi tập mỗi tuần",
            "train_location": "bạn tập ở nhà hay gym",
            "experience_level": "trình độ tập hiện tại",
            "budget_level": "mức ngân sách",
            "cook_time_preference": "thời gian nấu mong muốn",
        }
        human_fields = [labels.get(field, field) for field in missing_fields]
        joined = ", ".join(human_fields)
        return f"Để hỗ trợ đúng hơn cho yêu cầu `{intent}`, mình cần thêm: {joined}."

    def build_text_prompt(self, prompt: dict[str, object]) -> str:
        sections = [
            ("SYSTEM", prompt.get("system_prompt", "")),
            ("PROFILE", prompt.get("profile_summary", "")),
            ("PERSONALIZATION", prompt.get("personalization_summary", "")),
            ("HISTORY", self._format_history(prompt.get("history", []))),
            ("TOOL_RESULTS", self._format_json(prompt.get("tool_results", {}))),
            ("KB_CONTEXT", self._format_kb_context(prompt.get("kb_context", []))),
            ("USER_MESSAGE", prompt.get("message", "")),
            ("INTENT", prompt.get("intent", "")),
            ("RESPONSE_RULES", self.build_response_rules(prompt)),
        ]
        return "\n\n".join(
            f"[{title}]\n{content}" for title, content in sections if content not in ("", "[]", "{}")
        )

    def build_response_rules(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", "general_fitness_qa"))
        common_style_rule = (
            "Trả lời bằng tiếng Việt tự nhiên, có dấu, giọng điệu thân thiện như một trợ lý hữu ích."
            if intent == "general_fitness_qa"
            else "Trả lời bằng tiếng Việt tự nhiên, có dấu, giọng điệu thân thiện như một fitness coach."
        )
        common_rules = [
            common_style_rule,
            "Không lặp lại câu hỏi của user.",
            "Không echo prompt và không xuất code fence.",
            "Nếu có TOOL_RESULTS thì xem đó là dữ liệu đúng nhất.",
            "Nếu TOOL_RESULTS có số liệu thì phải dùng đúng các con số đó, không làm tròn và không tự đổi số.",
            "Không viết các nhãn như Final Answer, Answer hay Response.",
            "Chỉ viết phần trả lời cuối cùng cho user.",
        ]

        intent_rules = {
            "request_tdee_macro": (
                "Tóm tắt calories mục tiêu và macro trong 1-3 câu, "
                "nếu rõ thì nên nhắc đến protein, fat, carb."
            ),
            "request_meal_guidance": (
                "Gợi ý trực tiếp khung 3-5 bữa ăn, mỗi bữa có mục tiêu tương đối và món ví dụ ngắn gọn. "
                "Không nhắc tới TOOL_RESULTS, prompt hay quy tắc nội bộ. "
                "Ưu tiên format kiểu: Bữa sáng..., Bữa trưa..., Bữa phụ..., Bữa tối..."
            ),
            "request_workout_plan": (
                "Giải thích ngắn gọn lịch tập cho user theo kiểu coach, nêu split, số buổi và 1-2 lưu ý quan trọng. "
                "Không nhắc tên trường nội bộ hay dữ liệu hệ thống."
            ),
            "general_fitness_qa": (
                "Trả lời trực tiếp câu hỏi hiện tại một cách tự nhiên và hữu ích. "
                "Không nhắc đến tool, intent, safety case, prompt hay quy tắc nội bộ."
            ),
        }
        extra_rule = intent_rules.get(intent)
        if extra_rule:
            common_rules.append(extra_rule)
        if str(prompt.get("personalization_summary", "")).strip():
            common_rules.append(
                "Nếu có PERSONALIZATION thì hãy phản ánh các ưu tiên đó vào câu trả lời một cách tự nhiên."
            )
        return "\n".join(f"- {rule}" for rule in common_rules)

    def _format_history(self, history: object) -> str:
        if not isinstance(history, list):
            return ""
        return "\n".join(
            f"User: {item.get('user_message', '')}\nAssistant: {item.get('assistant_message', '')}"
            for item in history
            if isinstance(item, dict)
        )

    def _format_json(self, value: object) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except TypeError:
            return str(value)

    def _format_kb_context(self, value: object) -> str:
        if not isinstance(value, list):
            return ""

        sections: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            examples = item.get("examples", [])
            example_text = ""
            if isinstance(examples, list) and examples:
                example_text = " | Ví dụ: " + "; ".join(str(example) for example in examples[:3])
            if not title and not content:
                continue
            label = f"- {title}" if title else "- Context"
            body = f"{label}: {content}{example_text}" if content else label
            sections.append(body)
        return "\n".join(sections)
