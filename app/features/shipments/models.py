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
                      unique=True, nullable=False, index=True)
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
    tracking = relationship(
        "ShipmentTrackingEvent",
        back_populates="shipment",
        order_by="ShipmentTrackingEvent.id",
        cascade="all, delete-orphan",
    )


class ShipmentTrackingEvent(Base):
    """Append-only timeline of a shipment's journey.

    Rows are created automatically on every status change and can also be
    added manually by an admin as free-form checkpoints (e.g. "Arrived at
    Lahore hub") with an optional location.
    """

    __tablename__ = "shipment_tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    status = Column(Enum(ShipmentStatus), nullable=True)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shipment = relationship("Shipment", back_populates="tracking")
    changed_by = relationship("User")
