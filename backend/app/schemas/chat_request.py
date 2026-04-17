from pydantic import BaseModel, Field

from app.schemas.user_profile import UserProfilePatch


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    profile_patch: UserProfilePatch | None = None
