from pydantic import BaseModel


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    safety_flag: bool
    missing_fields: list[str]
    tool_results: dict[str, object]
