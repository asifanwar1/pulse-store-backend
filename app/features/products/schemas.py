from enum import Enum
from pydantic import AliasChoices, BaseModel, Field, field_serializer, model_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.features.media.schemas import MediaItem


class ProductSortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class ProductStatusFilter(str, Enum):
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class ProductCategoryFilter(str, Enum):
    ELECTRONICS = "ELECTRONICS"
    SPORTS = "SPORTS"
    CLOTHING = "CLOTHING"
    BEAUTY = "BEAUTY"
    BOOKS = "BOOKS"
    HOME = "HOME"
    GARDEN = "GARDEN"
    TOYS = "TOYS"
    FOOD = "FOOD"


class ProductPayloadBase(BaseModel):
    name: str
    sku: str
    brand: str
    description: Optional[str] = None
    retail_price: Decimal = Field(..., max_digits=10, decimal_places=2)
    cost_price: Decimal = Field(..., max_digits=10, decimal_places=2)
    stock_quantity: int = 0
    tags: list[str] = Field(default_factory=list)
    media: list[MediaItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status_stock_consistency(self):
        status = getattr(self, "status", None)
        if status == ProductStatusFilter.ACTIVE and self.stock_quantity <= 0:
            raise ValueError("stock_quantity must be greater than 0 when status is ACTIVE")
        if status == ProductStatusFilter.OUT_OF_STOCK and self.stock_quantity > 0:
            raise ValueError("stock_quantity must be 0 when status is OUT_OF_STOCK")
        return self


class ProductCreate(ProductPayloadBase):
    category_id: int = Field(validation_alias=AliasChoices("category_id", "category"))
    status: ProductStatusFilter


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    retail_price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    stock_quantity: Optional[int] = None
    category_id: Optional[int] = Field(None, validation_alias=AliasChoices("category_id", "category"))
    status: Optional[ProductStatusFilter] = None
    tags: Optional[list[str]] = None
    media: Optional[list[MediaItem]] = None


class ProductResponse(ProductPayloadBase):
    id: int
    slug: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("retail_price", "cost_price")
    def serialize_prices(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ProductListResponse(BaseModel):
    data: list[ProductResponse]
    count: int


class ProductAnalyticsMetric(BaseModel):
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


class ProductAnalyticsResponse(BaseModel):
    total_products: ProductAnalyticsMetric
    active_products: ProductAnalyticsMetric
    out_of_stock_products: ProductAnalyticsMetric
    average_price: ProductAnalyticsMetric
