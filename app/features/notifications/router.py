from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.notifications import service
from app.features.notifications.schemas import (
    DeviceTokenRegister,
    DeviceTokenUnregister,
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_notifications(db, current_user.id, page=page, limit=limit, is_read=is_read)


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"count": service.get_unread_count(db, current_user.id)}


@router.patch("/read-all", status_code=204)
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service.mark_all_read(db, current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.mark_read(db, current_user.id, notification_id)


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_notification(db, current_user.id, notification_id)


@router.post("/device-tokens", status_code=201)
def register_device_token(
    payload: DeviceTokenRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.register_device_token(db, current_user.id, payload.token, payload.platform)
    return {"status": "ok"}


@router.delete("/device-tokens", status_code=204)
def unregister_device_token(
    payload: DeviceTokenUnregister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.unregister_device_token(db, current_user.id, payload.token)
