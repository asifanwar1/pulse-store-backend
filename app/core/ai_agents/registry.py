from dataclasses import dataclass

from pydantic_ai import Agent

from app.core.ai_agents.deps import AgentDeps
from app.core.exceptions import NotFoundException


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    display_name: str
    agent: "Agent[AgentDeps, str]"
    default_model: str
    default_system_prompt: str
    requires_admin: bool = False


_REGISTRY: dict[str, AgentDefinition] = {}


def register_agent(definition: AgentDefinition) -> None:
    if definition.key in _REGISTRY:
        raise RuntimeError(f"Agent '{definition.key}' is already registered")
    _REGISTRY[definition.key] = definition


def get_agent_definition(key: str) -> AgentDefinition:
    try:
        return _REGISTRY[key]
    except KeyError:
        raise NotFoundException(f"Unknown agent '{key}'")


def list_agent_definitions() -> list[AgentDefinition]:
    return list(_REGISTRY.values())
