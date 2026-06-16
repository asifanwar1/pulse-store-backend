from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.orders.models import PaymentMethod
from app.features.revenue import service
from app.features.revenue.schemas import (
    RevenueAnalyticsResponse,
    RevenueListResponse,
    RevenueResponse,
    RevenueSortDirection,
)
from app.features.shipments.models import ShipmentStatus

router = APIRouter()


@router.get("/", response_model=RevenueListResponse)
def list_revenues(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    column: str = Query("created_at"),
    direction: RevenueSortDirection = Query(RevenueSortDirection.DESC),
    search: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None, ge=1),
    order_id: Optional[int] = Query(None, ge=1),
    shipment_id: Optional[int] = Query(None, ge=1),
    payment_method: Optional[PaymentMethod] = Query(None),
    shipment_status: Optional[ShipmentStatus] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_revenues(
        db,
        page=page,
        limit=limit,
        column=column,
        direction=direction,
        search=search,
        user_id=user_id,
        order_id=order_id,
        shipment_id=shipment_id,
        payment_method=payment_method,
        shipment_status=shipment_status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/analytics", response_model=RevenueAnalyticsResponse)
def get_revenue_analytics(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_revenue_analytics(db)


@router.get("/{revenue_id}", response_model=RevenueResponse)
def get_revenue(
    revenue_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_revenue_by_id(db, revenue_id)
