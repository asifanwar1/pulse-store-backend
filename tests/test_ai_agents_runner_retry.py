import asyncio
import json

from pydantic_ai import ModelHTTPError

from app.config import settings
from app.core.ai_agents.registry import AgentDefinition
from app.core.ai_agents.runner import ChatContext, stream_agent_chat


class _FakeResult:
    def __init__(self, text):
        self._text = text

    async def stream_text(self, delta=True):
        yield self._text

    def new_messages(self):
        return []


class _FakeRunStreamCM:
    def __init__(self, outcome):
        self._outcome = outcome

    async def __aenter__(self):
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return _FakeResult(self._outcome)

    async def __aexit__(self, *exc_info):
        return False


class _FakeAgent:
    """Stands in for a pydantic_ai.Agent: each call to run_stream() consumes the next
    scripted outcome -- either an exception to raise, or the reply text to "generate"."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)

    def run_stream(self, *args, **kwargs):
        return _FakeRunStreamCM(self._outcomes.pop(0))


def _make_ctx(agent):
    definition = AgentDefinition(
        key="fake_agent",
        display_name="Fake Agent",
        agent=agent,
        default_model="groq:llama-3.3-70b-versatile",
        default_system_prompt="You are a fake agent.",
    )
    return ChatContext(
        definition=definition,
        conversation_id=1,
        model_name=definition.default_model,
        deps=None,
        history=[],
        db=None,
    )


def _run(ctx, message="hello"):
    async def _collect():
        events = []
        async for raw_event in stream_agent_chat(ctx, message):
            payload = raw_event.removeprefix("data: ").rstrip("\n")
            events.append(json.loads(payload))
        return events

    return asyncio.run(_collect())


def _patch_append_turn(monkeypatch):
    saved = []
    monkeypatch.setattr(
        "app.features.ai_agents.service.append_turn",
        lambda db, conversation_id, new_messages, reply_text: saved.append(reply_text),
    )
    return saved


def test_stream_agent_chat_retries_once_after_groq_tool_use_failed(monkeypatch):
    saved = _patch_append_turn(monkeypatch)
    error = ModelHTTPError(status_code=400, model_name="groq:llama-3.3-70b-versatile")
    ctx = _make_ctx(_FakeAgent([error, "It worked."]))

    events = _run(ctx)

    assert [e["type"] for e in events] == ["delta", "done"]
    assert events[0]["text"] == "It worked."
    assert saved == ["It worked."]


def test_stream_agent_chat_gives_up_after_exhausting_retries(monkeypatch):
    saved = _patch_append_turn(monkeypatch)
    error = ModelHTTPError(status_code=400, model_name="groq:llama-3.3-70b-versatile")
    outcomes = [error] * (settings.AI_MODEL_RETRY_ATTEMPTS + 1)
    ctx = _make_ctx(_FakeAgent(outcomes))

    events = _run(ctx)

    assert [e["type"] for e in events] == ["error"]
    assert not saved
