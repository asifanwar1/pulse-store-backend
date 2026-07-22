from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.features.notifications.models import DeviceTokenPlatform, NotificationType


class NotificationResponse(BaseModel):
    id: int
    type: NotificationType
    title: str
    body: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    data: Optional[dict] = None
    is_read: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    data: list[NotificationResponse]
    count: int


class UnreadCountResponse(BaseModel):
    count: int


class DeviceTokenRegister(BaseModel):
    token: str
    platform: DeviceTokenPlatform


class DeviceTokenUnregister(BaseModel):
    token: str
