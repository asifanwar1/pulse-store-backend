from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.orders import service
from app.features.orders.schemas import (
    OrderAnalyticsResponse,
    OrderConfigResponse,
    OrderCreate,
    OrderDetailResponse,
    OrderListResponse,
    OrderSortDirection,
    OrderStatusUpdate,
    OrderResponse,
    OrderTrackingResponse,
)
from app.features.orders.models import OrderStatus
from app.features.auth.dependencies import get_current_user, get_current_admin_user
from app.features.users.models import User
from app.core.exceptions import ForbiddenException

router = APIRouter()


@router.get("/", response_model=OrderListResponse)
def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    column: str = Query("created_at"),
    direction: OrderSortDirection = Query(OrderSortDirection.DESC),
    search: Optional[str] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    user_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.is_admin:
        return service.get_orders(
            db,
            user_id=user_id,
            page=page,
            limit=limit,
            column=column,
            direction=direction,
            search=search,
            status=status,
        )
    if user_id is not None and user_id != current_user.id:
        raise ForbiddenException()
    return service.get_orders(
        db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        column=column,
        direction=direction,
        search=search,
        status=status,
    )


@router.get("/analytics", response_model=OrderAnalyticsResponse)
def get_orders_analytics(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_orders_analytics(db)


@router.get("/config", response_model=OrderConfigResponse)
def get_order_config():
    return service.get_order_config()


@router.post("/", response_model=OrderDetailResponse, status_code=201)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin and order_in.user_id != current_user.id:
        raise ForbiddenException()
    return service.create_order(db, order_in, actor_user_id=current_user.id)


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = service.get_order_by_id(db, order_id)
    if not current_user.is_admin and order.user_id != current_user.id:
        raise ForbiddenException()
    return order


@router.get("/{order_id}/tracking", response_model=OrderTrackingResponse)
def get_order_tracking(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = service.get_order_by_id(db, order_id)
    if not current_user.is_admin and order.user_id != current_user.id:
        raise ForbiddenException()
    return order


@router.patch("/{order_id}/status", response_model=OrderDetailResponse)
def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.update_order_status(db, order_id, status_in, actor_user_id=current_admin.id)
