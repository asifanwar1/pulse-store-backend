from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.features.users.models import User


@dataclass
class AgentDeps:
    """Shared dependency bundle every registered agent's tools receive via RunContext[AgentDeps].

    Deliberately has no `db` field: pydantic-ai can execute multiple tool calls from the same
    turn concurrently, and a sync SQLAlchemy Session is not safe to share across concurrent
    callers. Tools open their own short-lived session via tool_db_session() instead.
    """

    current_user: User
    system_prompt: str
    conversation_id: Optional[int] = None


@contextmanager
def tool_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def bind_dynamic_system_prompt(agent) -> None:
    """Resolve the system prompt fresh on every run instead of once at Agent() construction.

    dynamic=True re-evaluates the prompt even when message_history already contains an
    earlier SystemPromptPart, which matters here because the admin can edit
    system_prompt_override between turns of the same conversation.
    """
    agent.system_prompt(dynamic=True)(lambda ctx: ctx.deps.system_prompt)
