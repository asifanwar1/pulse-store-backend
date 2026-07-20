from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AgentConfig(Base):
    """Admin control surface for a registered agent -- one row per AgentDefinition.key."""

    __tablename__ = "ai_agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    model_name = Column(String, nullable=True)
    system_prompt_override = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def default_system_prompt(self) -> Optional[str]:
        """The agent's built-in prompt (from its agents/*.py file), for the admin UI to show
        as a starting point -- not a DB column, since it's defined in code, not configured."""
        from app.core.ai_agents import registry
        from app.core.exceptions import NotFoundException

        try:
            return registry.get_agent_definition(self.agent_key).default_system_prompt
        except NotFoundException:
            return None


class Conversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship(
        "AgentMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AgentMessage.id"
    )
    tickets = relationship("SupportTicket", back_populates="conversation")


class AgentMessage(Base):
    """One row per agent.run() turn -- message_data is what deserialize_turns() reads back.

    role/content are a denormalized best-effort preview of the assistant's reply,
    for a future admin transcript viewer; they are never used to rebuild history.
    """

    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    message_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class SupportTicket(Base):
    __tablename__ = "ai_support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    conversation = relationship("Conversation", back_populates="tickets")
