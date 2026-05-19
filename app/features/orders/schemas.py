from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.features.orders.models import OrderStatus, PaymentMethod


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> str:
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
    notes: Optional[str] = None
    total_amount: Decimal
    total_ordered_items: int = Field(serialization_alias="totalOrderedItems")
    user: OrderUserResponse
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: list[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderListResponse(BaseModel):
    data: list[OrderResponse]
    count: int
