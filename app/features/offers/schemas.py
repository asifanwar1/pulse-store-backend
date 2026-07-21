from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, model_validator

from app.features.offers.models import OfferScope


class OfferStatus(str, Enum):
    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class OfferPayloadBase(BaseModel):
    name: str
    description: Optional[str] = None
    discount_percentage: Decimal = Field(..., gt=0, le=100, max_digits=5, decimal_places=2)
    scope: OfferScope
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    category_ids: list[int] = Field(default_factory=list)
    included_product_ids: list[int] = Field(default_factory=list)
    excluded_product_ids: list[int] = Field(default_factory=list)


class OfferCreate(OfferPayloadBase):
    @model_validator(mode="after")
    def validate_offer(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.scope == OfferScope.ALL_CATEGORIES and self.category_ids:
            raise ValueError("category_ids must be empty when scope is ALL_CATEGORIES")
        if self.scope == OfferScope.SPECIFIC_CATEGORIES and not self.category_ids and not self.included_product_ids:
            raise ValueError("category_ids or included_product_ids is required when scope is SPECIFIC_CATEGORIES")
        if set(self.included_product_ids) & set(self.excluded_product_ids):
            raise ValueError("a product cannot be both included and excluded")
        return self


class OfferUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_percentage: Optional[Decimal] = Field(None, gt=0, le=100, max_digits=5, decimal_places=2)
    scope: Optional[OfferScope] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    category_ids: Optional[list[int]] = None
    included_product_ids: Optional[list[int]] = None
    excluded_product_ids: Optional[list[int]] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class OfferCategorySummary(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class OfferProductSummary(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class OfferResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount_percentage: Decimal
    scope: OfferScope
    start_date: datetime
    end_date: datetime
    is_active: bool
    status: OfferStatus
    categories: list[OfferCategorySummary] = Field(default_factory=list)
    included_products: list[OfferProductSummary] = Field(default_factory=list)
    excluded_products: list[OfferProductSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("discount_percentage")
    def serialize_discount_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OfferListResponse(BaseModel):
    data: list[OfferResponse]
    count: int


class ActiveOfferResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount_percentage: Decimal
    scope: OfferScope
    end_date: datetime
    categories: list[OfferCategorySummary] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @field_serializer("discount_percentage")
    def serialize_discount_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ActiveOffersListResponse(BaseModel):
    data: list[ActiveOfferResponse]
    count: int
