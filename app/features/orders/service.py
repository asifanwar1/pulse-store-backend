from typing import Optional
from sqlalchemy.orm import Session
from app.features.orders.models import Order, OrderItem
from app.features.orders.schemas import OrderCreate, OrderStatusUpdate
from app.features.products.models import Product
from app.core.exceptions import NotFoundException, ConflictException


def get_orders(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> list[Order]:
    query = db.query(Order)
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    return query.offset(skip).limit(limit).all()


def get_order_by_id(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")
    return order


def create_order(db: Session, user_id: int, order_in: OrderCreate) -> Order:
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

    order = Order(user_id=user_id, total_amount=total)
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
