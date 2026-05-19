from typing import Optional
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session
from app.features.orders.models import Order, OrderItem, OrderStatus
from app.features.orders.schemas import OrderCreate, OrderSortDirection, OrderStatusUpdate
from app.features.products.models import Product
from app.features.users.models import User
from app.core.exceptions import NotFoundException, ConflictException


SORTABLE_ORDER_COLUMNS = {
    "id": Order.id,
    "user_id": Order.user_id,
    "status": Order.status,
    "payment_method": Order.payment_method,
    "total_amount": Order.total_amount,
    "created_at": Order.created_at,
    "updated_at": Order.updated_at,
}


def get_orders(
    db: Session,
    user_id: Optional[int] = None,
    page: int = 1,
    limit: int = 10,
    column: str = "created_at",
    direction: OrderSortDirection = OrderSortDirection.DESC,
    search: Optional[str] = None,
    status: Optional[OrderStatus] = None,
) -> dict:
    query = db.query(Order).join(User)

    if user_id is not None:
        query = query.filter(Order.user_id == user_id)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    cast(Order.id, String).ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term),
                    cast(Order.status, String).ilike(search_term),
                    cast(Order.payment_method, String).ilike(search_term),
                )
            )

    if status is not None:
        query = query.filter(Order.status == status)

    total_count = query.count()

    sort_column = SORTABLE_ORDER_COLUMNS.get(column, Order.created_at)
    if direction == OrderSortDirection.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * limit
    orders = query.offset(offset).limit(limit).all()
    return {"data": orders, "count": total_count}


def get_order_by_id(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")
    return order


def create_order(db: Session, order_in: OrderCreate) -> Order:
    user = db.query(User).filter(User.id == order_in.user_id).first()
    if not user:
        raise NotFoundException(f"User {order_in.user_id} not found")

    total = 0
    resolved_items = []
    for item in order_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise NotFoundException(f"Product {item.product_id} not found")
        if product.stock_quantity < item.quantity:
            raise ConflictException(f"Insufficient stock for product: {product.name}")
        total += product.price * item.quantity
        resolved_items.append((product, item.quantity))

    order = Order(
        user_id=order_in.user_id,
        total_amount=total,
        payment_method=order_in.payment_method,
        notes=order_in.notes,
    )
    db.add(order)
    db.flush()

    for product, quantity in resolved_items:
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        ))
        product.stock_quantity -= quantity

    db.commit()
    db.refresh(order)
    return order


def update_order_status(db: Session, order_id: int, status_in: OrderStatusUpdate) -> Order:
    order = get_order_by_id(db, order_id)
    order.status = status_in.status
    db.commit()
    db.refresh(order)
    return order
