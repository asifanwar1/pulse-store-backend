from typing import Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session
from app.features.orders.models import Order, OrderItem, OrderStatus
from app.features.orders.schemas import (
    OrderAnalyticsMetric,
    OrderAnalyticsResponse,
    OrderCreate,
    OrderSortDirection,
    OrderStatusUpdate,
)
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


def _calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        if current == 0:
            return Decimal("0.00")
        return Decimal("100.00")
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_orders_analytics(db: Session) -> OrderAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    orders = db.query(Order.status, Order.total_amount, Order.created_at).all()
    previous_orders = [order for order in orders if order.created_at and order.created_at < period_start]

    current_total = Decimal(len(orders))
    previous_total = Decimal(len(previous_orders))

    current_pending = Decimal(sum(1 for order in orders if order.status == OrderStatus.PENDING))
    previous_pending = Decimal(sum(1 for order in previous_orders if order.status == OrderStatus.PENDING))

    current_shipped = Decimal(sum(1 for order in orders if order.status == OrderStatus.SHIPPED))
    previous_shipped = Decimal(sum(1 for order in previous_orders if order.status == OrderStatus.SHIPPED))

    current_revenue = sum(
        (_to_decimal(order.total_amount) for order in orders if order.status != OrderStatus.CANCELLED),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    previous_revenue = sum(
        (_to_decimal(order.total_amount) for order in previous_orders if order.status != OrderStatus.CANCELLED),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return OrderAnalyticsResponse(
        totalOrders=OrderAnalyticsMetric(
            value=int(current_total),
            change_percentage=_calculate_percentage_change(current_total, previous_total),
        ),
        pendingOrders=OrderAnalyticsMetric(
            value=int(current_pending),
            change_percentage=_calculate_percentage_change(current_pending, previous_pending),
        ),
        shippedOrders=OrderAnalyticsMetric(
            value=int(current_shipped),
            change_percentage=_calculate_percentage_change(current_shipped, previous_shipped),
        ),
        revenue=OrderAnalyticsMetric(
            value=current_revenue,
            change_percentage=_calculate_percentage_change(current_revenue, previous_revenue),
        ),
    )


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
