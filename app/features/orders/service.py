from typing import Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, selectinload
from app.features.notifications import service as notifications_service
from app.features.notifications.models import NotificationType
from app.features.offers import service as offers_service
from app.features.orders.models import Order, OrderItem, OrderSettings, OrderStatus, OrderStatusHistory
from app.features.orders.schemas import (
    OrderAnalyticsMetric,
    OrderAnalyticsResponse,
    OrderConfigResponse,
    OrderConfigUpdate,
    OrderCreate,
    OrderSortDirection,
    OrderStatusUpdate,
)
from app.features.products.models import Product
from app.features.users.models import User
from app.core.exceptions import NotFoundException, ConflictException
from app.core.money import to_decimal
from app.core.utils import calculate_percentage_change


DEFAULT_SHIPPING_FEE = Decimal("5.99")

ORDER_SETTINGS_ID = 1

TERMINAL_ORDER_STATUSES = (OrderStatus.DELIVERED, OrderStatus.CANCELLED)


SORTABLE_ORDER_COLUMNS = {
    "id": Order.id,
    "user_id": Order.user_id,
    "userId": Order.user_id,
    "status": Order.status,
    "payment_method": Order.payment_method,
    "paymentMethod": Order.payment_method,
    "total_amount": Order.total_amount,
    "totalAmount": Order.total_amount,
    "created_at": Order.created_at,
    "createdAt": Order.created_at,
    "updated_at": Order.updated_at,
    "updatedAt": Order.updated_at,
}


def apply_order_status(
    order: Order,
    status: OrderStatus,
    *,
    note: Optional[str] = None,
    changed_by_user_id: Optional[int] = None,
    force: bool = False,
) -> bool:
    """Set an order's status and append a tracking entry when it changes.

    No-op transitions are ignored (so a status that is re-applied does not
    create duplicate timeline rows) unless ``force`` is set, which is used to
    record the initial entry when an order is created. Returns whether an entry
    was recorded. The caller is responsible for committing the session.
    """
    if not force and order.status == status:
        return False
    if not force and order.status in TERMINAL_ORDER_STATUSES:
        raise ConflictException(
            f"Order is already {order.status.value.lower()} and cannot change status")
    previous_status = order.status
    order.status = status
    order.tracking.append(
        OrderStatusHistory(
            status=status,
            note=note,
            changed_by_user_id=changed_by_user_id,
        )
    )
    if status == OrderStatus.CANCELLED and previous_status != OrderStatus.CANCELLED:
        for item in order.items:
            if item.product is not None:
                item.product.stock_quantity += item.quantity
    return True


def get_or_create_order_settings(db: Session) -> OrderSettings:
    settings = db.query(OrderSettings).filter(
        OrderSettings.id == ORDER_SETTINGS_ID).first()
    if not settings:
        settings = OrderSettings(
            id=ORDER_SETTINGS_ID, shipping_fee=DEFAULT_SHIPPING_FEE)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_order_config(db: Session) -> OrderConfigResponse:
    settings = get_or_create_order_settings(db)
    return OrderConfigResponse(shipping_fee=settings.shipping_fee)


def update_order_config(
    db: Session,
    config_in: OrderConfigUpdate,
    actor_user_id: Optional[int] = None,
) -> OrderConfigResponse:
    settings = get_or_create_order_settings(db)
    settings.shipping_fee = config_in.shipping_fee
    settings.updated_by = actor_user_id
    db.commit()
    db.refresh(settings)
    return OrderConfigResponse(shipping_fee=settings.shipping_fee)


def get_orders_analytics(db: Session) -> OrderAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    orders = db.query(Order.status, Order.total_amount, Order.created_at).all()
    previous_orders = [
        order for order in orders if order.created_at and order.created_at < period_start]

    current_total = Decimal(len(orders))
    previous_total = Decimal(len(previous_orders))

    current_pending = Decimal(
        sum(1 for order in orders if order.status == OrderStatus.PENDING))
    previous_pending = Decimal(
        sum(1 for order in previous_orders if order.status == OrderStatus.PENDING))

    current_shipped = Decimal(
        sum(1 for order in orders if order.status == OrderStatus.SHIPPED))
    previous_shipped = Decimal(
        sum(1 for order in previous_orders if order.status == OrderStatus.SHIPPED))

    current_revenue = sum(
        (to_decimal(order.total_amount)
         for order in orders if order.status != OrderStatus.CANCELLED),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    previous_revenue = sum(
        (to_decimal(order.total_amount)
         for order in previous_orders if order.status != OrderStatus.CANCELLED),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return OrderAnalyticsResponse(
        totalOrders=OrderAnalyticsMetric(
            value=int(current_total),
            change_percentage=calculate_percentage_change(
                current_total, previous_total),
        ),
        pendingOrders=OrderAnalyticsMetric(
            value=int(current_pending),
            change_percentage=calculate_percentage_change(
                current_pending, previous_pending),
        ),
        shippedOrders=OrderAnalyticsMetric(
            value=int(current_shipped),
            change_percentage=calculate_percentage_change(
                current_shipped, previous_shipped),
        ),
        revenue=OrderAnalyticsMetric(
            value=current_revenue,
            change_percentage=calculate_percentage_change(
                current_revenue, previous_revenue),
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
    query = db.query(Order).options(selectinload(Order.shipments)).join(User)

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
    order = (
        db.query(Order)
        .options(selectinload(Order.shipments), selectinload(Order.tracking))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise NotFoundException("Order not found")
    return order


def create_order(db: Session, order_in: OrderCreate, actor_user_id: Optional[int] = None) -> Order:
    user = db.query(User).filter(User.id == order_in.user_id).first()
    if not user:
        raise NotFoundException(f"User {order_in.user_id} not found")

    product_ids = {item.product_id for item in order_in.items}
    products_by_id = {
        product.id: product
        for product in db.query(Product)
        .filter(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
        .all()
    }

    resolved_items = []
    for item in order_in.items:
        product = products_by_id.get(item.product_id)
        if not product:
            raise NotFoundException(f"Product {item.product_id} not found")
        if product.stock_quantity < item.quantity:
            raise ConflictException(
                f"Insufficient stock for product: {product.name}")
        resolved_items.append((product, item.quantity))

    offer_matches = offers_service.compute_offer_matches(
        db, [product for product, _ in resolved_items])

    shipping_fee = get_or_create_order_settings(db).shipping_fee

    total = Decimal("0")
    order = Order(
        user_id=order_in.user_id,
        total_amount=total,
        shipping_fee=shipping_fee,
        payment_method=order_in.payment_method,
        notes=order_in.notes,
    )
    db.add(order)
    db.flush()

    for product, quantity in resolved_items:
        match = offer_matches.get(product.id)
        unit_price = match.discounted_price if match else to_decimal(
            product.price)
        total += unit_price * quantity
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
        ))
        product.stock_quantity -= quantity

    order.total_amount = total + order.shipping_fee
    apply_order_status(
        order,
        OrderStatus.PENDING,
        note="Order placed",
        changed_by_user_id=actor_user_id,
        force=True,
    )
    db.commit()
    db.refresh(order)

    notifications_service.notify_admins(
        db,
        NotificationType.NEW_ORDER,
        title="New order placed",
        body=f"Order #{order.id} placed by {user.full_name} for {order.total_amount:.2f}",
        entity_type="order",
        entity_id=order.id,
    )
    return get_order_by_id(db, order.id)


def update_order_status(
    db: Session,
    order_id: int,
    status_in: OrderStatusUpdate,
    actor_user_id: Optional[int] = None,
) -> Order:
    order = get_order_by_id(db, order_id)
    status_changed = apply_order_status(
        order, status_in.status, changed_by_user_id=actor_user_id)
    db.commit()

    if status_changed:
        notifications_service.create_notification(
            db,
            order.user_id,
            NotificationType.ORDER_STATUS_CHANGED,
            title="Order status updated",
            body=f"Your order #{order.id} is now {order.status.value.lower()}",
            entity_type="order",
            entity_id=order.id,
        )
    return get_order_by_id(db, order_id)
