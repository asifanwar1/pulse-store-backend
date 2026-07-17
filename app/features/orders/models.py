import enum
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from decimal import Decimal


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPING = "SHIPPING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    card = "CARD"
    cod = "COD"
    bank_transfer = "BANK_TRANSFER"
    wallet = "WALLET"


class OrderPaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_method = Column(Enum(PaymentMethod),
                            default=PaymentMethod.cod, nullable=False)
    payment_status = Column(Enum(OrderPaymentStatus), default=OrderPaymentStatus.UNPAID, nullable=False)
    notes = Column(Text, nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    shipments = relationship("Shipment", back_populates="order")
    tracking = relationship(
        "OrderStatusHistory",
        back_populates="order",
        order_by="OrderStatusHistory.id",
        cascade="all, delete-orphan",
    )

    @property
    def total_ordered_items(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def latest_shipment(self):
        if not self.shipments:
            return None
        return max(self.shipments, key=lambda shipment: shipment.id)

    @property
    def estimated_delivery_date(self):
        shipment = self.latest_shipment
        return shipment.estimated_delivery_date if shipment else None

    @property
    def shipped_at(self):
        shipment = self.latest_shipment
        return shipment.shipped_at if shipment else None


class OrderStatusHistory(Base):
    """Append-only timeline of an order's status transitions (order tracking)."""

    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus), nullable=False)
    note = Column(Text, nullable=True)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="tracking")
    changed_by = relationship("User")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    @property
    def product_name(self) -> str:
        return self.product.name if self.product else ""

    @property
    def product_sku(self) -> str:
        return self.product.sku if self.product else ""

    @property
    def product_category(self) -> str | None:
        return self.product.category.name if self.product and self.product.category else None

    @property
    def total_amount(self) -> Decimal:
        return self.unit_price * self.quantity
