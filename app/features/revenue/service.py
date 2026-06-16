from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import NotFoundException
from app.features.orders.models import Order, OrderItem, OrderStatus, PaymentMethod
from app.features.products.models import Product
from app.features.revenue.schemas import (
    RevenueAnalyticsMetric,
    RevenueAnalyticsResponse,
    RevenueCompletedOrderResponse,
    RevenueCustomerResponse,
    RevenueOrderItemResponse,
    RevenueResponse,
    RevenueSortDirection,
)
from app.features.shipments.models import Shipment, ShipmentStatus
from app.features.users.models import User


SORTABLE_REVENUE_COLUMNS = {
    "id": Order.id,
    "order_id": Order.id,
    "orderId": Order.id,
    "user_id": Order.user_id,
    "userId": Order.user_id,
    "payment_method": Order.payment_method,
    "paymentMethod": Order.payment_method,
    "total_amount": Order.total_amount,
    "totalAmount": Order.total_amount,
    "revenue_amount": Order.total_amount,
    "revenueAmount": Order.total_amount,
    "created_at": Order.created_at,
    "createdAt": Order.created_at,
    "updated_at": Order.updated_at,
    "updatedAt": Order.updated_at,
    "delivered_at": Shipment.delivered_at,
    "deliveredAt": Shipment.delivered_at,
}


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value) -> Decimal:
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        if current == 0:
            return Decimal("0.00")
        return Decimal("100.00")
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _revenue_details_options():
    return (
        joinedload(Order.user),
        selectinload(Order.shipments),
        selectinload(Order.items)
        .joinedload(OrderItem.product)
        .joinedload(Product.category),
    )


def _build_item_response(item: OrderItem) -> RevenueOrderItemResponse:
    product = item.product
    retail_price = _money(item.unit_price)
    cost_price = _money(product.cost_price if product else 0)
    total_amount = _money(retail_price * Decimal(item.quantity))
    profit = _money((retail_price - cost_price) * Decimal(item.quantity))

    return RevenueOrderItemResponse(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product_name,
        product_sku=item.product_sku,
        product_category=item.product_category,
        quantity=item.quantity,
        retail_price=retail_price,
        cost_price=cost_price,
        total_amount=total_amount,
        profit=profit,
    )


def _build_revenue_response(order: Order) -> RevenueResponse:
    customer = None
    if order.user:
        customer = RevenueCustomerResponse(
            id=order.user.id,
            name=order.user.full_name,
            email=order.user.email,
            phone=order.user.phone_number,
        )

    order_items = [_build_item_response(item) for item in order.items]
    profit = _money(sum((item.profit for item in order_items), Decimal("0")))

    return RevenueResponse(
        id=order.id,
        order_id=order.id,
        revenue_amount=_money(order.total_amount),
        profit=profit,
        completed_order=RevenueCompletedOrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            payment_method=order.payment_method,
            notes=order.notes,
            total_amount=_money(order.total_amount),
            total_ordered_items=order.total_ordered_items,
            created_at=order.created_at,
            updated_at=order.updated_at,
            customer=customer,
        ),
        order_items=order_items,
        shipment_details=order.shipments,
    )


def _calculate_order_profit(order: Order) -> Decimal:
    return _money(
        sum(
            (
                (_money(item.unit_price) - _money(item.product.cost_price if item.product else 0))
                * Decimal(item.quantity)
                for item in order.items
            ),
            Decimal("0"),
        )
    )


def _base_revenue_query(db: Session):
    return (
        db.query(Order)
        .options(*_revenue_details_options())
        .join(User)
        .outerjoin(Shipment)
        .filter(Order.status == OrderStatus.DELIVERED)
    )


def get_revenue_analytics(db: Session) -> RevenueAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    orders = (
        db.query(Order)
        .options(
            selectinload(Order.items)
            .joinedload(OrderItem.product)
        )
        .filter(Order.status == OrderStatus.DELIVERED)
        .all()
    )
    previous_orders = [
        order for order in orders if order.created_at and order.created_at < period_start
    ]

    current_completed_orders = Decimal(len(orders))
    previous_completed_orders = Decimal(len(previous_orders))
    current_revenue = _money(sum((_to_decimal(order.total_amount) for order in orders), Decimal("0")))
    previous_revenue = _money(sum((_to_decimal(order.total_amount) for order in previous_orders), Decimal("0")))
    current_profit = _money(sum((_calculate_order_profit(order) for order in orders), Decimal("0")))
    previous_profit = _money(sum((_calculate_order_profit(order) for order in previous_orders), Decimal("0")))

    return RevenueAnalyticsResponse(
        completedOrders=RevenueAnalyticsMetric(
            value=int(current_completed_orders),
            change_percentage=_calculate_percentage_change(current_completed_orders, previous_completed_orders),
        ),
        totalRevenue=RevenueAnalyticsMetric(
            value=current_revenue,
            change_percentage=_calculate_percentage_change(current_revenue, previous_revenue),
        ),
        totalProfit=RevenueAnalyticsMetric(
            value=current_profit,
            change_percentage=_calculate_percentage_change(current_profit, previous_profit),
        ),
    )


def get_revenues(
    db: Session,
    page: int = 1,
    limit: int = 10,
    column: str = "created_at",
    direction: RevenueSortDirection = RevenueSortDirection.DESC,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
    order_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    payment_method: Optional[PaymentMethod] = None,
    shipment_status: Optional[ShipmentStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    query = _base_revenue_query(db)

    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    if order_id is not None:
        query = query.filter(Order.id == order_id)
    if shipment_id is not None:
        query = query.filter(Shipment.id == shipment_id)
    if payment_method is not None:
        query = query.filter(Order.payment_method == payment_method)
    if shipment_status is not None:
        query = query.filter(Shipment.status == shipment_status)
    if date_from is not None:
        query = query.filter(Order.created_at >= date_from)
    if date_to is not None:
        query = query.filter(Order.created_at <= date_to)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    cast(Order.id, String).ilike(search_term),
                    cast(Order.user_id, String).ilike(search_term),
                    cast(Order.payment_method, String).ilike(search_term),
                    cast(Order.total_amount, String).ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term),
                    Shipment.tracking_id.ilike(search_term),
                    Shipment.courier.ilike(search_term),
                )
            )

    total_count = query.count()

    sort_column = SORTABLE_REVENUE_COLUMNS.get(column, Order.created_at)
    if direction == RevenueSortDirection.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * limit
    orders = query.offset(offset).limit(limit).all()
    return {"data": [_build_revenue_response(order) for order in orders], "count": total_count}


def get_revenue_by_id(db: Session, revenue_id: int) -> RevenueResponse:
    order = (
        _base_revenue_query(db)
        .filter(Order.id == revenue_id)
        .first()
    )
    if not order:
        raise NotFoundException("Revenue record not found")
    return _build_revenue_response(order)
