from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.agent_service import run_agent

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    reply = run_agent(
        db=db,
        user=current_user,
        messages=messages,
        dashboard_id=payload.dashboard_id,
    )
    return ChatResponse(reply=reply)
