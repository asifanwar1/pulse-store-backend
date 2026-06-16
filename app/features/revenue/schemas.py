from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.features.orders.models import OrderStatus, PaymentMethod
from app.features.shipments.models import ShipmentMethod, ShipmentStatus


class RevenueSortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class RevenueCustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None


class RevenueCompletedOrderResponse(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    payment_method: PaymentMethod
    notes: Optional[str] = None
    total_amount: Decimal
    total_ordered_items: int = Field(serialization_alias="totalOrderedItems")
    created_at: datetime
    updated_at: Optional[datetime] = None
    customer: Optional[RevenueCustomerResponse] = None

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"


class RevenueOrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    product_category: Optional[str] = None
    quantity: int
    retail_price: Decimal
    cost_price: Decimal
    total_amount: Decimal
    profit: Decimal

    @field_serializer("retail_price", "cost_price", "total_amount", "profit")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class RevenueShipmentResponse(BaseModel):
    id: int
    order_id: int
    tracking_id: str
    shipment_method: ShipmentMethod
    courier: str
    status: ShipmentStatus
    estimated_delivery_date: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RevenueResponse(BaseModel):
    id: int
    order_id: int
    created_at: datetime
    revenue_amount: Decimal
    profit: Decimal
    completed_order: RevenueCompletedOrderResponse
    order_items: list[RevenueOrderItemResponse] = Field(default_factory=list)
    shipment_details: list[RevenueShipmentResponse] = Field(default_factory=list)

    @field_serializer("revenue_amount", "profit")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class RevenueListResponse(BaseModel):
    data: list[RevenueResponse]
    count: int


class RevenueAnalyticsMetric(BaseModel):
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


class RevenueAnalyticsResponse(BaseModel):
    completedOrders: RevenueAnalyticsMetric
    totalRevenue: RevenueAnalyticsMetric
    totalProfit: RevenueAnalyticsMetric
