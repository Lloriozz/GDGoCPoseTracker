from pydantic import BaseModel

from app.core.text_utils import normalize_text


RED_FLAG_KEYWORDS = {
    "dau nguc",
    "dau that nguc",
    "kho tho",
    "ngat",
    "chong mat nang",
    "co giat",
    "dau dau du doi",
    "chan thuong nang",
    "xuat huyet",
    "kho cu dong",
    "tim dap bat thuong",
}


class SafetyResult(BaseModel):
    is_unsafe: bool
    reason: str | None = None
    response: str | None = None


class SafetyChecker:
    def evaluate(self, message: str) -> SafetyResult:
        lowered = normalize_text(message)
        for keyword in RED_FLAG_KEYWORDS:
            if keyword in lowered:
                return SafetyResult(
                    is_unsafe=True,
                    reason=f"Detected red-flag symptom: {keyword}",
                    response=(
                        "Mình không nên tư vấn tập luyện tiếp trong trường hợp này. "
                        "Bạn nên dừng tập ngay và đi khám hoặc liên hệ nhân viên y tế sớm, "
                        "đặc biệt vì bạn đang mô tả dấu hiệu cần được đánh giá trực tiếp."
                    ),
                )

        return SafetyResult(is_unsafe=False)
