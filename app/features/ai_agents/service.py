from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.ai_agents import registry
from app.core.ai_agents.messages import serialize_new_messages
from app.core.exceptions import BadRequestException, NotFoundException
from app.features.ai_agents.models import AgentConfig, AgentMessage, Conversation, SupportTicket
from app.features.ai_agents.schemas import (
    AgentConfigUpdate,
    AgentStatusUpdate,
    SupportTicketAnalyticsMetric,
    SupportTicketAnalyticsResponse,
    SupportTicketStatusUpdate,
)
from app.features.notifications import service as notifications_service
from app.features.notifications.models import NotificationType
from app.core.utils import calculate_percentage_change
from app.features.ai_agents import model_catalog


def get_or_create_agent_config(db: Session, agent_key: str) -> AgentConfig:
    config = db.query(AgentConfig).filter(AgentConfig.agent_key == agent_key).first()
    if config:
        return config

    definition = registry.get_agent_definition(agent_key)
    config = AgentConfig(agent_key=definition.key, display_name=definition.display_name, is_enabled=True)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def list_agent_configs(db: Session) -> dict:
    for definition in registry.list_agent_definitions():
        get_or_create_agent_config(db, definition.key)

    configs = db.query(AgentConfig).order_by(AgentConfig.agent_key).all()
    return {"data": configs, "count": len(configs)}


def update_agent_config(db: Session, agent_key: str, update_in: AgentConfigUpdate, updated_by: int) -> AgentConfig:
    config = get_or_create_agent_config(db, agent_key)
    update_data = update_in.model_dump(exclude_unset=True)
    if update_data.get("model_name"):
        valid_models = {entry["model"] for entry in model_catalog.list_available_models()}
        if update_data["model_name"] not in valid_models:
            raise BadRequestException(f"Unknown model '{update_data['model_name']}'")
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_by = updated_by
    db.commit()
    db.refresh(config)
    return config


def set_agent_status(db: Session, agent_key: str, status_in: AgentStatusUpdate, updated_by: int) -> AgentConfig:
    config = get_or_create_agent_config(db, agent_key)
    config.is_enabled = status_in.is_enabled
    config.updated_by = updated_by
    db.commit()
    db.refresh(config)
    return config


def get_or_create_conversation(
    db: Session, agent_key: str, user_id: int, conversation_id: Optional[int]
) -> Conversation:
    if conversation_id is not None:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.agent_key == agent_key,
            )
            .first()
        )
        if not conversation:
            raise NotFoundException("Conversation not found")
        return conversation

    conversation = Conversation(agent_key=agent_key, user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def load_conversation_turns(db: Session, conversation_id: int, max_turns: int) -> list[list[dict]]:
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.id.desc())
        .limit(max_turns)
        .all()
    )
    rows.reverse()
    return [row.message_data for row in rows]


def append_turn(db: Session, conversation_id: int, new_messages: list, reply_text: str) -> None:
    if not new_messages:
        return
    message = AgentMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=reply_text[:2000] or None,
        message_data=serialize_new_messages(new_messages),
    )
    db.add(message)
    db.commit()


def create_support_ticket(db: Session, conversation_id: int, user_id: int, subject: str, message: str) -> SupportTicket:
    ticket = SupportTicket(conversation_id=conversation_id, user_id=user_id, subject=subject, message=message)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    notifications_service.notify_admins(
        db,
        NotificationType.SUPPORT_TICKET_CREATED,
        title="New support ticket",
        body=subject,
        entity_type="support_ticket",
        entity_id=ticket.id,
    )
    return ticket


def list_support_tickets(db: Session, is_resolved: Optional[bool], page: int, limit: int) -> dict:
    query = db.query(SupportTicket)
    if is_resolved is not None:
        query = query.filter(SupportTicket.is_resolved.is_(is_resolved))

    total_count = query.count()
    offset = (page - 1) * limit
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()
    return {"data": tickets, "count": total_count}


def _resolution_rate(resolved: int, total: int) -> int:
    if total == 0:
        return 0
    return int((Decimal(resolved) / Decimal(total) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_tickets_analytics(db: Session) -> SupportTicketAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)

    all_tickets = db.query(SupportTicket.is_resolved, SupportTicket.created_at).all()
    previous_tickets = [ticket for ticket in all_tickets if ticket.created_at and ticket.created_at < period_start]

    current_total = len(all_tickets)
    current_resolved = sum(1 for ticket in all_tickets if ticket.is_resolved)
    current_unresolved = current_total - current_resolved
    current_rate = _resolution_rate(current_resolved, current_total)

    previous_total = len(previous_tickets)
    previous_resolved = sum(1 for ticket in previous_tickets if ticket.is_resolved)
    previous_unresolved = previous_total - previous_resolved
    previous_rate = _resolution_rate(previous_resolved, previous_total)

    return SupportTicketAnalyticsResponse(
        totalTickets=SupportTicketAnalyticsMetric(
            value=current_total,
            change_percentage=calculate_percentage_change(Decimal(current_total), Decimal(previous_total)),
        ),
        resolvedTickets=SupportTicketAnalyticsMetric(
            value=current_resolved,
            change_percentage=calculate_percentage_change(Decimal(current_resolved), Decimal(previous_resolved)),
        ),
        unresolvedTickets=SupportTicketAnalyticsMetric(
            value=current_unresolved,
            change_percentage=calculate_percentage_change(Decimal(current_unresolved), Decimal(previous_unresolved)),
        ),
        resolutionRate=SupportTicketAnalyticsMetric(
            value=current_rate,
            change_percentage=calculate_percentage_change(Decimal(current_rate), Decimal(previous_rate)),
        ),
    )


def set_ticket_status(db: Session, ticket_id: int, status_in: SupportTicketStatusUpdate, actor_user_id: int) -> SupportTicket:
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundException("Support ticket not found")

    ticket.is_resolved = status_in.is_resolved
    ticket.resolved_at = datetime.now(timezone.utc) if status_in.is_resolved else None
    ticket.resolved_by = actor_user_id if status_in.is_resolved else None
    db.commit()
    db.refresh(ticket)

    if status_in.is_resolved:
        notifications_service.create_notification(
            db,
            ticket.user_id,
            NotificationType.SUPPORT_TICKET_RESOLVED,
            title="Support ticket resolved",
            body=f"Your support ticket '{ticket.subject}' has been resolved.",
            entity_type="support_ticket",
            entity_id=ticket.id,
        )
    return ticket
