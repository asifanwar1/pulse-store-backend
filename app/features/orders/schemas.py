from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.features.orders.models import OrderPaymentStatus, OrderStatus, PaymentMethod


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    product_category: Optional[str]
    quantity: int
    unit_price: Decimal
    total_amount: Decimal

    model_config = {"from_attributes": True}

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> str:
        return f"{value:.2f}"

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderCreate(BaseModel):
    user_id: int
    items: list[OrderItemCreate]
    payment_method: PaymentMethod = PaymentMethod.cod
    notes: Optional[str] = None


class OrderSortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderAnalyticsMetric(BaseModel):
    value: int | Decimal
    change_percentage: Decimal

    @field_serializer("value")
    def serialize_value(self, value: int | Decimal) -> int | str:
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        return value

    @field_serializer("change_percentage")
    def serialize_change_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderAnalyticsResponse(BaseModel):
    totalOrders: OrderAnalyticsMetric
    pendingOrders: OrderAnalyticsMetric
    shippedOrders: OrderAnalyticsMetric
    revenue: OrderAnalyticsMetric


class OrderUserResponse(BaseModel):
    id: int
    name: str = Field(validation_alias="full_name")
    email: str

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: OrderPaymentStatus
    notes: Optional[str] = None
    total_amount: Decimal
    total_ordered_items: int = Field(serialization_alias="totalOrderedItems")
    user: OrderUserResponse
    created_at: datetime
    updated_at: Optional[datetime] = None
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    items: list[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderListResponse(BaseModel):
    data: list[OrderResponse]
    count: int
