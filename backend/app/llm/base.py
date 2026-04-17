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
