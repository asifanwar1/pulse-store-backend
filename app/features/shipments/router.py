from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException
from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.shipments import service
from app.features.shipments.models import ShipmentStatus
from app.features.shipments.schemas import (
    ShipmentAnalyticsResponse,
    ShipmentCreate,
    ShipmentDetailResponse,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentSortDirection,
    ShipmentStatusUpdate,
    ShipmentTrackingByNumberResponse,
    ShipmentTrackingEventCreate,
    ShipmentTrackingResponse,
    ShipmentUpdate,
)
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=ShipmentListResponse)
def list_shipments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    column: str = Query("created_at"),
    direction: ShipmentSortDirection = Query(ShipmentSortDirection.DESC),
    search: Optional[str] = Query(None),
    status: Optional[ShipmentStatus] = Query(None),
    order_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_shipments(
        db,
        page=page,
        limit=limit,
        column=column,
        direction=direction,
        search=search,
        status=status,
        order_id=order_id,
    )


@router.get("/analytics", response_model=ShipmentAnalyticsResponse)
def get_shipments_analytics(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_shipments_analytics(db)


@router.get("/track/{tracking_id}", response_model=ShipmentTrackingByNumberResponse)
def track_shipment(
    tracking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Track a shipment by its tracking number.

    Requires authentication: admins can track any shipment; customers can only
    track shipments belonging to their own orders. Returns status and timeline
    only — no customer or order details.
    """
    shipment = service.get_shipment_by_tracking_id(db, tracking_id)
    if not current_user.is_admin and shipment.order.user_id != current_user.id:
        raise ForbiddenException()
    return shipment


@router.post("/", response_model=ShipmentDetailResponse, status_code=201)
def create_shipment(
    shipment_in: ShipmentCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.create_shipment(db, shipment_in, actor_user_id=current_admin.id)


@router.get("/{shipment_id}", response_model=ShipmentDetailResponse)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_shipment_by_id(db, shipment_id)


@router.get("/{shipment_id}/tracking", response_model=ShipmentTrackingResponse)
def get_shipment_tracking(
    shipment_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_shipment_by_id(db, shipment_id)


@router.post("/{shipment_id}/tracking", response_model=ShipmentDetailResponse, status_code=201)
def add_shipment_tracking_event(
    shipment_id: int,
    event_in: ShipmentTrackingEventCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.add_shipment_tracking_event(db, shipment_id, event_in, actor_user_id=current_admin.id)


@router.patch("/{shipment_id}", response_model=ShipmentDetailResponse)
def update_shipment(
    shipment_id: int,
    shipment_in: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.update_shipment(db, shipment_id, shipment_in, actor_user_id=current_admin.id)


@router.patch("/{shipment_id}/status", response_model=ShipmentDetailResponse)
def update_shipment_status(
    shipment_id: int,
    status_in: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.update_shipment_status(db, shipment_id, status_in, actor_user_id=current_admin.id)
