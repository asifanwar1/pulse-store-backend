from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.features.orders.schemas import OrderItemResponse
from app.features.shipments.models import ShipmentMethod, ShipmentStatus


class ShipmentSortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class ShipmentPayloadBase(BaseModel):
    order_id: int
    tracking_id: str
    shipment_method: ShipmentMethod
    courier: str
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
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ShipmentCustomerResponse(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class ShipmentAddressResponse(BaseModel):
    street: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = ""


class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    tracking_id: str
    shipment_method: ShipmentMethod
    courier: str
    status: ShipmentStatus
    shipment_address: Optional[ShipmentAddressResponse] = None
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    order: Optional[ShipmentOrderSummary] = None
    customer: Optional[ShipmentCustomerResponse] = None
    ordered_items: list[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ShipmentListResponse(BaseModel):
    data: list[ShipmentResponse]
    count: int


class ShipmentTrackingEventCreate(BaseModel):
    description: str = Field(min_length=1)
    location: Optional[str] = None
    status: Optional[ShipmentStatus] = None


class ShipmentTrackingEventResponse(BaseModel):
    id: int
    status: Optional[ShipmentStatus] = None
    description: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShipmentDetailResponse(ShipmentResponse):
    tracking: list[ShipmentTrackingEventResponse] = Field(default_factory=list)


class ShipmentTrackingResponse(BaseModel):
    shipment_id: int = Field(validation_alias="id")
    tracking_id: str
    status: ShipmentStatus
    estimated_delivery_date: Optional[datetime] = None
    tracking: list[ShipmentTrackingEventResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ShipmentTrackingByNumberResponse(BaseModel):
    """Tracking-number lookup view (customer or admin).

    A tracking-focused projection — status, dates and timeline only, no
    customer or order details.
    """

    tracking_id: str
    status: ShipmentStatus
    courier: str
    shipment_method: ShipmentMethod
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    tracking: list[ShipmentTrackingEventResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ShipmentAnalyticsMetric(BaseModel):
    value: int
    change_percentage: Decimal

    @field_serializer("change_percentage")
    def serialize_change_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ShipmentAnalyticsResponse(BaseModel):
    totalShipments: ShipmentAnalyticsMetric
    inTransit: ShipmentAnalyticsMetric
    delivered: ShipmentAnalyticsMetric
    failed: ShipmentAnalyticsMetric
