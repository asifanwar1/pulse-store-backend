from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.features.shipments.models import ShipmentMethod, ShipmentStatus


class ShipmentSortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class ShipmentPayloadBase(BaseModel):
    order_id: int
    tracking_id: str
    shipment_method: ShipmentMethod
    courier: str
    shipping_address: Optional[dict[str, Any]] = None
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class ShipmentCreate(ShipmentPayloadBase):
    status: ShipmentStatus = ShipmentStatus.PENDING


class ShipmentUpdate(BaseModel):
    order_id: Optional[int] = None
    tracking_id: Optional[str] = None
    shipment_method: Optional[ShipmentMethod] = None
    courier: Optional[str] = None
    status: Optional[ShipmentStatus] = None
    shipping_address: Optional[dict[str, Any]] = None
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus


class ShipmentOrderSummary(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: str

    model_config = ConfigDict(from_attributes=True)


class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    tracking_id: str
    shipment_method: ShipmentMethod
    courier: str
    status: ShipmentStatus
    shipping_address: Optional[dict[str, Any]] = None
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    order: Optional[ShipmentOrderSummary] = None

    model_config = ConfigDict(from_attributes=True)


class ShipmentListResponse(BaseModel):
    data: list[ShipmentResponse]
    count: int
