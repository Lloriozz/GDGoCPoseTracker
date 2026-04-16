from fastapi import APIRouter

from app.core.orchestrator import FitnessChatOrchestrator
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse


router = APIRouter()
orchestrator = FitnessChatOrchestrator()


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return orchestrator.handle_chat(request)
