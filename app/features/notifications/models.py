import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class NotificationType(str, enum.Enum):
    ORDER_STATUS_CHANGED = "order_status_changed"
    NEW_ORDER = "new_order"
    SUPPORT_TICKET_CREATED = "support_ticket_created"
    SUPPORT_TICKET_RESOLVED = "support_ticket_resolved"
    WALLET_PAYMENT_SUCCEEDED = "wallet_payment_succeeded"
    WALLET_PAYMENT_FAILED = "wallet_payment_failed"


class DeviceTokenPlatform(str, enum.Enum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)

    type = Column(
        Enum(NotificationType, name="notification_type",
             native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)

    # Lets the frontend deep-link a notification to the record it's about,
    # e.g. entity_type="order", entity_id=42 -> that order's detail page.
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    data = Column(JSONB, nullable=True)

    is_read = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    platform = Column(
        Enum(DeviceTokenPlatform, name="device_token_platform",
             native_enum=False, length=10, values_callable=_enum_values),
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True),
                          server_default=func.now(), onupdate=func.now())
