from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class _CatalogEntry:
    model: str
    provider: str
    label: str
    note: str
    requires_key: str
    """Name of the Settings attribute that must be non-empty for this model to work."""


_CATALOG: list[_CatalogEntry] = [
    _CatalogEntry(
        "groq:llama-3.3-70b-versatile", "groq", "Llama 3.3 70B Versatile",
        "Recommended default — balanced quality and speed", "GROQ_API_KEY",
    ),
    _CatalogEntry(
        "groq:llama-3.1-8b-instant", "groq", "Llama 3.1 8B Instant",
        "Fastest — lighter reasoning, good for quick testing", "GROQ_API_KEY",
    ),
    _CatalogEntry(
        "groq:openai/gpt-oss-20b", "groq", "GPT-OSS 20B (via Groq)",
        "Strong tool-calling, OpenAI's open-weight model", "GROQ_API_KEY",
    ),
    _CatalogEntry(
        "groq:openai/gpt-oss-120b", "groq", "GPT-OSS 120B (via Groq)",
        "Best quality of the Groq options; tighter free-tier rate limits", "GROQ_API_KEY",
    ),
    _CatalogEntry(
        "openai:gpt-4o-mini", "openai", "GPT-4o mini",
        "Fast and inexpensive", "OPENAI_API_KEY",
    ),
    _CatalogEntry(
        "anthropic:claude-haiku-4-5-20251001", "anthropic", "Claude Haiku 4.5",
        "Fast, strong tool-calling", "ANTHROPIC_API_KEY",
    ),
]


def list_available_models() -> list[dict]:
    return [
        {
            "model": entry.model,
            "provider": entry.provider,
            "label": entry.label,
            "note": entry.note,
            "available": bool(getattr(settings, entry.requires_key, "")),
        }
        for entry in _CATALOG
    ]
