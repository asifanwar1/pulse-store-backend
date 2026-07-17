from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentConfigResponse(BaseModel):
    id: int
    agent_key: str
    display_name: str
    is_enabled: bool
    model_name: Optional[str] = None
    system_prompt_override: Optional[str] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentConfigListResponse(BaseModel):
    data: list[AgentConfigResponse]
    count: int


class AgentConfigUpdate(BaseModel):
    model_name: Optional[str] = None
    system_prompt_override: Optional[str] = None


class AgentStatusUpdate(BaseModel):
    is_enabled: bool = Field(...)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[int] = None


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
