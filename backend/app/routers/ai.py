from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import ChatRequest, ChatResponse
from app.services.ai_agent import run_chat

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatResponse:
    reply = run_chat(session, user, payload.message)
    return ChatResponse(reply=reply)
