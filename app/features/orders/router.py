from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.orders import service
from app.features.orders.schemas import OrderCreate, OrderStatusUpdate, OrderResponse
from app.features.auth.dependencies import get_current_user, get_current_admin_user
from app.features.users.models import User
from app.core.exceptions import ForbiddenException

router = APIRouter()


@router.get("/", response_model=list[OrderResponse])
def list_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.is_admin:
        return service.get_orders(db, skip=skip, limit=limit)
    return service.get_orders(db, user_id=current_user.id, skip=skip, limit=limit)


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.create_order(db, current_user.id, order_in)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = service.get_order_by_id(db, order_id)
    if not current_user.is_admin and order.user_id != current_user.id:
        raise ForbiddenException()
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: int, status_in: OrderStatusUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_order_status(db, order_id, status_in)
