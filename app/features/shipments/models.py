import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ShipmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class ShipmentMethod(str, enum.Enum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    OVERNIGHT = "OVERNIGHT"
    PICKUP = "PICKUP"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"),
                      nullable=False, index=True)
    tracking_id = Column(String, unique=True, nullable=False, index=True)
    shipment_method = Column(Enum(ShipmentMethod), nullable=False)
    courier = Column(String, nullable=False)
    status = Column(Enum(ShipmentStatus),
                    default=ShipmentStatus.PENDING, nullable=False, index=True)
    estimated_delivery_date = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    order = relationship("Order", back_populates="shipments")
