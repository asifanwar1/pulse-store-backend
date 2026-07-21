import json
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.ai_agents import registry
from app.core.ai_agents.deps import AgentDeps
from app.core.ai_agents.messages import deserialize_turns
from app.core.exceptions import ForbiddenException
from app.features.media.schemas import MediaItem
from app.features.users.models import User


@dataclass
class ChatContext:
    definition: "registry.AgentDefinition"
    conversation_id: int
    model_name: str
    deps: AgentDeps
    history: list
    db: Session


def prepare_chat_context(
    db: Session,
    agent_key: str,
    current_user: User,
    conversation_id: Optional[int] = None,
) -> ChatContext:
    """Runs every synchronous check/lookup before the response starts streaming.

    Kept separate from stream_agent_chat() so auth/validation failures raise a normal
    HTTPException instead of surfacing inside an already-started SSE stream.
    """
    from app.features.ai_agents import service as ai_service

    definition = registry.get_agent_definition(agent_key)

    if definition.requires_admin and not current_user.is_admin:
        raise ForbiddenException("Admin access required")

    config = ai_service.get_or_create_agent_config(db, agent_key)
    if not settings.AI_AGENTS_ENABLED or not config.is_enabled:
        raise ForbiddenException(f"The {definition.display_name} is currently disabled")

    conversation = ai_service.get_or_create_conversation(db, agent_key, current_user.id, conversation_id)
    prior_turns = ai_service.load_conversation_turns(db, conversation.id, max_turns=settings.AI_CHAT_MAX_HISTORY_TURNS)

    deps = AgentDeps(
        current_user=current_user,
        system_prompt=config.system_prompt_override or definition.default_system_prompt,
        conversation_id=conversation.id,
        is_first_message=not prior_turns,
    )
    return ChatContext(
        definition=definition,
        conversation_id=conversation.id,
        model_name=config.model_name or definition.default_model,
        deps=deps,
        history=deserialize_turns(prior_turns),
        db=db,
    )


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _append_media_block(message: str, media: Optional[list[MediaItem]]) -> str:
    """Renders attached media as plain text the agent can read and hand to a tool.

    Agents are text-only (no vision model wired up) -- they never see the actual image
    bytes/pixels, only this id/url/file_name listing, which is exactly the shape
    `MediaItem` tool parameters (e.g. product_listing's create_product_draft) expect.
    """
    if not media:
        return message

    lines = ["[Attached images]"]
    for item in media:
        name = item.file_name or item.url.rsplit("/", 1)[-1]
        lines.append(f"- id: {item.id}, url: {item.url}, file_name: {name}")

    return f"{message}\n\n{chr(10).join(lines)}" if message.strip() else "\n".join(lines)


async def stream_agent_chat(
    ctx: ChatContext, message: str, media: Optional[list[MediaItem]] = None
) -> AsyncGenerator[str, None]:
    from app.features.ai_agents import service as ai_service

    reply_chunks: list[str] = []
    try:
        async with ctx.definition.agent.run_stream(
            _append_media_block(message, media),
            deps=ctx.deps,
            message_history=ctx.history,
            model=ctx.model_name,
        ) as result:
            async for chunk in result.stream_text(delta=True):
                reply_chunks.append(chunk)
                yield _sse({"type": "delta", "text": chunk})
            ai_service.append_turn(
                ctx.db,
                ctx.conversation_id,
                result.new_messages(),
                reply_text="".join(reply_chunks),
            )
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "done", "conversation_id": ctx.conversation_id})
