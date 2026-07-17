from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.ai_agents import registry
from app.core.ai_agents.messages import serialize_new_messages
from app.core.exceptions import NotFoundException
from app.features.ai_agents.models import AgentConfig, AgentMessage, Conversation, SupportTicket
from app.features.ai_agents.schemas import AgentConfigUpdate, AgentStatusUpdate, SupportTicketStatusUpdate


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
    return ticket


def list_support_tickets(db: Session, is_resolved: Optional[bool], page: int, limit: int) -> dict:
    query = db.query(SupportTicket)
    if is_resolved is not None:
        query = query.filter(SupportTicket.is_resolved.is_(is_resolved))

    total_count = query.count()
    offset = (page - 1) * limit
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()
    return {"data": tickets, "count": total_count}


def set_ticket_status(db: Session, ticket_id: int, status_in: SupportTicketStatusUpdate, actor_user_id: int) -> SupportTicket:
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundException("Support ticket not found")

    ticket.is_resolved = status_in.is_resolved
    ticket.resolved_at = datetime.now(timezone.utc) if status_in.is_resolved else None
    ticket.resolved_by = actor_user_id if status_in.is_resolved else None
    db.commit()
    db.refresh(ticket)
    return ticket
