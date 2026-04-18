from fastapi import APIRouter

from app.core.orchestrator import FitnessChatOrchestrator
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse


router = APIRouter()
orchestrator = FitnessChatOrchestrator()


def normalize_user_id(user_id: str) -> str:
    """Normalize user_id to handle UUID format from Supabase vs mobile app format."""
    # Handle UUID format from Supabase (lowercase for consistency)
    if "-" in user_id and len(user_id) == 36:
        return user_id.lower()
    
    # Handle mobile app temporary IDs
    if user_id.startswith("mobile-user-"):
        return user_id
    
    # Return as-is for other formats
    return user_id


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Normalize user_id to handle Supabase UUID format
    normalized_request = ChatRequest(
        user_id=normalize_user_id(request.user_id),
        session_id=request.session_id,
        message=request.message,
        profile_patch=request.profile_patch
    )
    return orchestrator.handle_chat(normalized_request)
