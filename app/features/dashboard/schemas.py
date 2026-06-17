from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_serializer


class DashboardMetric(BaseModel):
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


class DashboardStatsResponse(BaseModel):
    totalRevenue: DashboardMetric
    totalOrders: DashboardMetric
    totalCustomers: DashboardMetric
    totalProducts: DashboardMetric
    avgOrderValue: DashboardMetric
    conversionRate: DashboardMetric


class RevenueOverviewItem(BaseModel):
    month: str
    revenue: Decimal
    expenses: Decimal
    profit: Decimal

    @field_serializer("revenue", "expenses", "profit")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class RevenueOverviewResponse(BaseModel):
    year: int
    data: list[RevenueOverviewItem]


class OrdersByCategoryItem(BaseModel):
    category_id: Optional[int] = None
    category: str
    orders: int
    revenue: Decimal

    @field_serializer("revenue")
    def serialize_revenue(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrdersByCategoryResponse(BaseModel):
    year: int
    data: list[OrdersByCategoryItem]


class SalesDistributionItem(BaseModel):
    category_id: Optional[int] = None
    category: str
    revenue: Decimal
    percentage: Decimal

    @field_serializer("revenue", "percentage")
    def serialize_decimals(self, value: Decimal) -> str:
        return f"{value:.2f}"


class SalesDistributionResponse(BaseModel):
    year: int
    data: list[SalesDistributionItem]


class CustomerGrowthItem(BaseModel):
    month: str
    newCustomers: int
    returningCustomers: int


class CustomerGrowthResponse(BaseModel):
    year: int
    data: list[CustomerGrowthItem]


class WeeklySalesItem(BaseModel):
    day: str
    revenue: Decimal
    orders: int

    @field_serializer("revenue")
    def serialize_revenue(self, value: Decimal) -> str:
        return f"{value:.2f}"


class WeeklySalesResponse(BaseModel):
    weekStart: str
    weekEnd: str
    data: list[WeeklySalesItem]


class TopProductItem(BaseModel):
    rank: int
    product_id: int
    name: str
    sku: str
    category: Optional[str] = None
    revenue: Decimal
    sales: int
    stock: int
    change_percentage: Decimal

    @field_serializer("revenue", "change_percentage")
    def serialize_decimals(self, value: Decimal) -> str:
        return f"{value:.2f}"


class TopProductsResponse(BaseModel):
    data: list[TopProductItem]
    count: int


class LowStockAlertItem(BaseModel):
    product_id: int
    name: str
    sku: str
    category: Optional[str] = None
    stock: int
    reorderThreshold: int
    severity: str
    stockPercentage: Decimal

    @field_serializer("stockPercentage")
    def serialize_stock_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class LowStockAlertsResponse(BaseModel):
    data: list[LowStockAlertItem]
    count: int
