from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core import push
from app.core.exceptions import NotFoundException
from app.features.notifications.models import DeviceToken, DeviceTokenPlatform, Notification, NotificationType
from app.features.users.models import User, UserType


def _send_push_to_user(db: Session, user_id: int, title: str, body: str, data: dict) -> None:
    tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
    if not tokens:
        return

    web_tokens = [t.token for t in tokens if t.platform ==
                  DeviceTokenPlatform.WEB]
    expo_tokens = [t.token for t in tokens if t.platform !=
                   DeviceTokenPlatform.WEB]

    invalid_tokens = push.send_fcm_push(web_tokens, title, body, data) + push.send_expo_push(
        expo_tokens, title, body, data
    )
    if invalid_tokens:
        db.query(DeviceToken).filter(DeviceToken.token.in_(
            invalid_tokens)).delete(synchronize_session=False)
        db.commit()


def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    body: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    data: Optional[dict] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    _send_push_to_user(
        db,
        user_id,
        title,
        body,
        {"type": notification_type.value, "entity_type": entity_type or "",
            "entity_id": entity_id or ""},
    )
    return notification


def notify_admins(
    db: Session,
    notification_type: NotificationType,
    title: str,
    body: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    data: Optional[dict] = None,
) -> None:
    admin_ids = [row.id for row in db.query(User.id).filter(
        User.user_type == UserType.ADMIN.value).all()]
    for admin_id in admin_ids:
        create_notification(
            db, admin_id, notification_type, title, body, entity_type=entity_type, entity_id=entity_id, data=data
        )


def get_notifications(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
    is_read: Optional[bool] = None,
) -> dict:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if is_read is not None:
        query = query.filter(Notification.is_read.is_(is_read))

    total_count = query.count()
    offset = (page - 1) * limit
    notifications = query.order_by(
        Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {"data": notifications, "count": total_count}


def get_unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .count()
    )


def _get_owned_notification(db: Session, user_id: int, notification_id: int) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notification:
        raise NotFoundException("Notification not found")
    return notification


def mark_read(db: Session, user_id: int, notification_id: int) -> Notification:
    notification = _get_owned_notification(db, user_id, notification_id)
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> None:
    db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read.is_(False)).update(
        {"is_read": True}
    )
    db.commit()


def delete_notification(db: Session, user_id: int, notification_id: int) -> None:
    notification = _get_owned_notification(db, user_id, notification_id)
    db.delete(notification)
    db.commit()


def register_device_token(db: Session, user_id: int, token: str, platform: DeviceTokenPlatform) -> DeviceToken:
    device_token = db.query(DeviceToken).filter(
        DeviceToken.token == token).first()
    now = datetime.now(timezone.utc)

    if device_token:
        device_token.user_id = user_id
        device_token.platform = platform
        device_token.last_seen_at = now
    else:
        device_token = DeviceToken(
            user_id=user_id, token=token, platform=platform)
        db.add(device_token)

    db.commit()
    db.refresh(device_token)
    return device_token


def unregister_device_token(db: Session, user_id: int, token: str) -> None:
    db.query(DeviceToken).filter(DeviceToken.token == token, DeviceToken.user_id == user_id).delete(
        synchronize_session=False
    )
    db.commit()
