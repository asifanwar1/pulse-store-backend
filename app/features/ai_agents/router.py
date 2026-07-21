from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.ai_agents import runner
from app.dependencies import get_db
from app.features.ai_agents import agents  # noqa: F401  (populates the agent registry)
from app.features.ai_agents import model_catalog, service
from app.features.ai_agents.schemas import (
    AgentConfigListResponse,
    AgentConfigResponse,
    AgentConfigUpdate,
    AgentStatusUpdate,
    AvailableModelsResponse,
    ChatRequest,
    SupportTicketAnalyticsResponse,
    SupportTicketListResponse,
    SupportTicketResponse,
    SupportTicketStatusUpdate,
)
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=AgentConfigListResponse)
def list_agent_configs(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.list_agent_configs(db)


@router.get("/available-models", response_model=AvailableModelsResponse)
def list_available_models(_=Depends(get_current_admin_user)):
    return {"data": model_catalog.list_available_models()}


@router.patch("/{agent_key}", response_model=AgentConfigResponse)
def update_agent_config(
    agent_key: str,
    update_in: AgentConfigUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.update_agent_config(db, agent_key, update_in, updated_by=current_admin.id)


@router.patch("/{agent_key}/status", response_model=AgentConfigResponse)
def update_agent_status(
    agent_key: str,
    status_in: AgentStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.set_agent_status(db, agent_key, status_in, updated_by=current_admin.id)


@router.post("/{agent_key}/chat")
async def chat_with_agent(
    agent_key: str,
    chat_in: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ctx = runner.prepare_chat_context(db, agent_key, current_user, chat_in.conversation_id)
    return StreamingResponse(runner.stream_agent_chat(ctx, chat_in.message), media_type="text/event-stream")


@router.get("/tickets/analytics", response_model=SupportTicketAnalyticsResponse)
def get_tickets_analytics(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_tickets_analytics(db)


@router.get("/tickets", response_model=SupportTicketListResponse)
def list_support_tickets(
    is_resolved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.list_support_tickets(db, is_resolved=is_resolved, page=page, limit=limit)


@router.patch("/tickets/{ticket_id}/status", response_model=SupportTicketResponse)
def update_ticket_status(
    ticket_id: int,
    status_in: SupportTicketStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.set_ticket_status(db, ticket_id, status_in, actor_user_id=current_admin.id)
