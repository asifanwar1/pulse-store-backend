from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictException, NotFoundException
from app.features.orders.models import Order, OrderItem, OrderStatus
from app.features.orders.schemas import OrderItemResponse
from app.features.products.models import Product
from app.features.shipments.models import Shipment, ShipmentStatus
from app.features.shipments.schemas import (
    ShipmentAddressResponse,
    ShipmentAnalyticsMetric,
    ShipmentAnalyticsResponse,
    ShipmentCustomerResponse,
    ShipmentCreate,
    ShipmentSortDirection,
    ShipmentStatusUpdate,
    ShipmentUpdate,
)


SORTABLE_SHIPMENT_COLUMNS = {
    "id": Shipment.id,
    "order_id": Shipment.order_id,
    "orderId": Shipment.order_id,
    "tracking_id": Shipment.tracking_id,
    "trackingId": Shipment.tracking_id,
    "shipment_method": Shipment.shipment_method,
    "shipmentMethod": Shipment.shipment_method,
    "courier": Shipment.courier,
    "status": Shipment.status,
    "estimated_delivery_date": Shipment.estimated_delivery_date,
    "estimatedDeliveryDate": Shipment.estimated_delivery_date,
    "shipped_at": Shipment.shipped_at,
    "shippedAt": Shipment.shipped_at,
    "delivered_at": Shipment.delivered_at,
    "deliveredAt": Shipment.delivered_at,
    "created_at": Shipment.created_at,
    "createdAt": Shipment.created_at,
    "updated_at": Shipment.updated_at,
    "updatedAt": Shipment.updated_at,
}


IN_TRANSIT_STATUSES = (
    ShipmentStatus.SHIPPED,
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.OUT_FOR_DELIVERY,
)
FAILED_STATUSES = (
    ShipmentStatus.CANCELLED,
    ShipmentStatus.RETURNED,
)


def _calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        if current == 0:
            return Decimal("0.00")
        return Decimal("100.00")
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_order(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException(f"Order {order_id} not found")
    return order


def _ensure_tracking_id_available(db: Session, tracking_id: str, shipment_id: Optional[int] = None) -> None:
    query = db.query(Shipment).filter(Shipment.tracking_id == tracking_id)
    if shipment_id is not None:
        query = query.filter(Shipment.id != shipment_id)
    if query.first():
        raise ConflictException("Shipment tracking ID already exists")


def _ensure_order_has_no_shipment(db: Session, order_id: int, shipment_id: Optional[int] = None) -> None:
    query = db.query(Shipment).filter(Shipment.order_id == order_id)
    if shipment_id is not None:
        query = query.filter(Shipment.id != shipment_id)
    if query.first():
        raise ConflictException("Order already has a shipment")


def _sync_order_status(order: Order, shipment_status: ShipmentStatus) -> None:
    if shipment_status == ShipmentStatus.DELIVERED:
        order.status = OrderStatus.DELIVERED
    elif shipment_status in (ShipmentStatus.SHIPPED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY):
        order.status = OrderStatus.SHIPPING
    elif shipment_status in (ShipmentStatus.CANCELLED, ShipmentStatus.RETURNED):
        order.status = OrderStatus.CANCELLED


def _mark_order_shipping_on_shipment_creation(order: Order) -> None:
    if order.status in (OrderStatus.PENDING, OrderStatus.PROCESSING):
        order.status = OrderStatus.SHIPPING


def _apply_status_timestamps(shipment: Shipment, status: ShipmentStatus) -> None:
    now = datetime.now(timezone.utc)
    if status in (ShipmentStatus.SHIPPED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY) and shipment.shipped_at is None:
        shipment.shipped_at = now
    if status == ShipmentStatus.DELIVERED and shipment.delivered_at is None:
        shipment.delivered_at = now


def _normalize_shipment_address(address: dict | None) -> ShipmentAddressResponse | None:
    if not address:
        return None
    return ShipmentAddressResponse(
        street=address.get("street") or address.get("street_address") or "",
        city=address.get("city") or "",
        state=address.get("state") or "",
        zip=address.get("zip") or address.get("zipcode") or "",
        country=address.get("country") or "",
    )


def _shipment_details_options():
    return (
        joinedload(Shipment.order).joinedload(Order.user),
        joinedload(Shipment.order)
        .selectinload(Order.items)
        .joinedload(OrderItem.product)
        .joinedload(Product.category),
    )


def _attach_response_details(shipments: list[Shipment]) -> list[Shipment]:
    for shipment in shipments:
        order = shipment.order
        user = order.user if order else None
        shipment.customer = (
            ShipmentCustomerResponse(
                name=user.full_name,
                email=user.email,
                phone=user.phone_number,
            )
            if user
            else None
        )
        shipment.ordered_items = (
            [OrderItemResponse.model_validate(item) for item in order.items]
            if order
            else []
        )
        shipment.shipment_address = _normalize_shipment_address(user.address if user else None)
    return shipments


def get_shipments_analytics(db: Session) -> ShipmentAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    shipments = db.query(Shipment.status, Shipment.created_at).all()
    previous_shipments = [
        shipment
        for shipment in shipments
        if shipment.created_at and shipment.created_at < period_start
    ]

    current_total = Decimal(len(shipments))
    previous_total = Decimal(len(previous_shipments))

    current_in_transit = Decimal(sum(1 for shipment in shipments if shipment.status in IN_TRANSIT_STATUSES))
    previous_in_transit = Decimal(sum(1 for shipment in previous_shipments if shipment.status in IN_TRANSIT_STATUSES))

    current_delivered = Decimal(sum(1 for shipment in shipments if shipment.status == ShipmentStatus.DELIVERED))
    previous_delivered = Decimal(sum(1 for shipment in previous_shipments if shipment.status == ShipmentStatus.DELIVERED))

    current_failed = Decimal(sum(1 for shipment in shipments if shipment.status in FAILED_STATUSES))
    previous_failed = Decimal(sum(1 for shipment in previous_shipments if shipment.status in FAILED_STATUSES))

    return ShipmentAnalyticsResponse(
        totalShipments=ShipmentAnalyticsMetric(
            value=int(current_total),
            change_percentage=_calculate_percentage_change(current_total, previous_total),
        ),
        inTransit=ShipmentAnalyticsMetric(
            value=int(current_in_transit),
            change_percentage=_calculate_percentage_change(current_in_transit, previous_in_transit),
        ),
        delivered=ShipmentAnalyticsMetric(
            value=int(current_delivered),
            change_percentage=_calculate_percentage_change(current_delivered, previous_delivered),
        ),
        failed=ShipmentAnalyticsMetric(
            value=int(current_failed),
            change_percentage=_calculate_percentage_change(current_failed, previous_failed),
        ),
    )


def get_shipments(
    db: Session,
    page: int = 1,
    limit: int = 10,
    column: str = "created_at",
    direction: ShipmentSortDirection = ShipmentSortDirection.DESC,
    search: Optional[str] = None,
    status: Optional[ShipmentStatus] = None,
    order_id: Optional[int] = None,
) -> dict:
    query = db.query(Shipment).options(*_shipment_details_options()).join(Order)

    if order_id is not None:
        query = query.filter(Shipment.order_id == order_id)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    cast(Shipment.id, String).ilike(search_term),
                    cast(Shipment.order_id, String).ilike(search_term),
                    Shipment.tracking_id.ilike(search_term),
                    Shipment.courier.ilike(search_term),
                    cast(Shipment.shipment_method, String).ilike(search_term),
                    cast(Shipment.status, String).ilike(search_term),
                )
            )

    if status is not None:
        query = query.filter(Shipment.status == status)

    total_count = query.count()

    sort_column = SORTABLE_SHIPMENT_COLUMNS.get(column, Shipment.created_at)
    if direction == ShipmentSortDirection.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * limit
    shipments = _attach_response_details(query.offset(offset).limit(limit).all())
    return {"data": shipments, "count": total_count}


def get_shipment_by_id(db: Session, shipment_id: int) -> Shipment:
    shipment = (
        db.query(Shipment)
        .options(*_shipment_details_options())
        .filter(Shipment.id == shipment_id)
        .first()
    )
    if not shipment:
        raise NotFoundException("Shipment not found")
    return _attach_response_details([shipment])[0]


def create_shipment(db: Session, shipment_in: ShipmentCreate) -> Shipment:
    order = _get_order(db, shipment_in.order_id)
    _ensure_order_has_no_shipment(db, shipment_in.order_id)
    _ensure_tracking_id_available(db, shipment_in.tracking_id)

    shipment = Shipment(
        order_id=shipment_in.order_id,
        tracking_id=shipment_in.tracking_id,
        shipment_method=shipment_in.shipment_method,
        courier=shipment_in.courier,
        status=shipment_in.status,
        estimated_delivery_date=shipment_in.estimated_delivery_date,
        shipped_at=shipment_in.shipped_at,
        delivered_at=shipment_in.delivered_at,
        notes=shipment_in.notes,
    )
    _apply_status_timestamps(shipment, shipment.status)
    _mark_order_shipping_on_shipment_creation(order)
    _sync_order_status(order, shipment.status)

    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return get_shipment_by_id(db, shipment.id)


def update_shipment(db: Session, shipment_id: int, shipment_in: ShipmentUpdate) -> Shipment:
    shipment = get_shipment_by_id(db, shipment_id)
    update_data = shipment_in.model_dump(exclude_unset=True)

    if "order_id" in update_data:
        _ensure_order_has_no_shipment(db, update_data["order_id"], shipment.id)
        shipment.order = _get_order(db, update_data["order_id"])
        shipment.order_id = update_data["order_id"]
    if "tracking_id" in update_data and update_data["tracking_id"] != shipment.tracking_id:
        _ensure_tracking_id_available(db, update_data["tracking_id"], shipment.id)
        shipment.tracking_id = update_data["tracking_id"]
    if "shipment_method" in update_data:
        shipment.shipment_method = update_data["shipment_method"]
    if "courier" in update_data:
        shipment.courier = update_data["courier"]
    if "estimated_delivery_date" in update_data:
        shipment.estimated_delivery_date = update_data["estimated_delivery_date"]
    if "shipped_at" in update_data:
        shipment.shipped_at = update_data["shipped_at"]
    if "delivered_at" in update_data:
        shipment.delivered_at = update_data["delivered_at"]
    if "notes" in update_data:
        shipment.notes = update_data["notes"]
    if "status" in update_data and update_data["status"] is not None:
        shipment.status = update_data["status"]
        _apply_status_timestamps(shipment, shipment.status)
        _sync_order_status(shipment.order, shipment.status)

    db.commit()
    db.refresh(shipment)
    return get_shipment_by_id(db, shipment.id)


def update_shipment_status(db: Session, shipment_id: int, status_in: ShipmentStatusUpdate) -> Shipment:
    shipment = get_shipment_by_id(db, shipment_id)
    shipment.status = status_in.status
    _apply_status_timestamps(shipment, shipment.status)
    _sync_order_status(shipment.order, shipment.status)
    db.commit()
    db.refresh(shipment)
    return get_shipment_by_id(db, shipment.id)
