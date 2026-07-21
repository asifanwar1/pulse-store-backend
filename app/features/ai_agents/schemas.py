from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.features.media.schemas import MediaItem


class AgentConfigResponse(BaseModel):
    id: int
    agent_key: str
    display_name: str
    is_enabled: bool
    model_name: Optional[str] = None
    system_prompt_override: Optional[str] = None
    default_system_prompt: Optional[str] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentConfigListResponse(BaseModel):
    data: list[AgentConfigResponse]
    count: int


class AvailableModel(BaseModel):
    model: str
    provider: str
    label: str
    note: str
    available: bool
    """False when the backend doesn't have the API key this model's provider needs."""


class AvailableModelsResponse(BaseModel):
    data: list[AvailableModel]


class AgentConfigUpdate(BaseModel):
    model_name: Optional[str] = None
    system_prompt_override: Optional[str] = None


class AgentStatusUpdate(BaseModel):
    is_enabled: bool = Field(...)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[int] = None
    media: Optional[list[MediaItem]] = None
    """Images the admin already uploaded via POST /media/upload, attached to this message."""


class SupportTicketResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    subject: str
    message: str
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SupportTicketListResponse(BaseModel):
    data: list[SupportTicketResponse]
    count: int


class SupportTicketStatusUpdate(BaseModel):
    is_resolved: bool = Field(...)


class SupportTicketAnalyticsMetric(BaseModel):
    value: int
    change_percentage: Decimal

    @field_serializer("change_percentage")
    def serialize_change_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class SupportTicketAnalyticsResponse(BaseModel):
    totalTickets: SupportTicketAnalyticsMetric
    resolvedTickets: SupportTicketAnalyticsMetric
    unresolvedTickets: SupportTicketAnalyticsMetric
    resolutionRate: SupportTicketAnalyticsMetric
    """Resolved tickets as a percentage (0-100) of total tickets."""
