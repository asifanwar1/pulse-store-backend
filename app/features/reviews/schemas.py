from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_serializer


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    user_id: int
    customer_name: str
    rating: int
    comment: Optional[str] = None
    is_hidden: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReviewListResponse(BaseModel):
    data: list[ReviewResponse]
    count: int


class ReviewVisibilityUpdate(BaseModel):
    is_hidden: bool = Field(...)


class ReviewAnalyticsMetric(BaseModel):
    value: int
    change_percentage: Decimal

    @field_serializer("change_percentage")
    def serialize_change_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ReviewAnalyticsResponse(BaseModel):
    total_reviews: ReviewAnalyticsMetric
    total_products_reviewed: ReviewAnalyticsMetric
    products_with_bad_reviews: ReviewAnalyticsMetric
    products_with_good_reviews: ReviewAnalyticsMetric
