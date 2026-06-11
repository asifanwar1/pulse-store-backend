from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.shipments import service
from app.features.shipments.models import ShipmentStatus
from app.features.shipments.schemas import (
    ShipmentCreate,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentSortDirection,
    ShipmentStatusUpdate,
    ShipmentUpdate,
)

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


@router.post("/", response_model=ShipmentResponse, status_code=201)
def create_shipment(
    shipment_in: ShipmentCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.create_shipment(db, shipment_in)


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_shipment_by_id(db, shipment_id)


@router.patch("/{shipment_id}", response_model=ShipmentResponse)
def update_shipment(
    shipment_id: int,
    shipment_in: ShipmentUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.update_shipment(db, shipment_id, shipment_in)


@router.patch("/{shipment_id}/status", response_model=ShipmentResponse)
def update_shipment_status(
    shipment_id: int,
    status_in: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.update_shipment_status(db, shipment_id, status_in)
