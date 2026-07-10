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
    INACTIVE = "INACTIVE"
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


class ProductTotalSalesUpdate(BaseModel):
    total_sales: int = Field(..., ge=0)


class ProductResponse(ProductPayloadBase):
    id: int
    slug: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: str
    total_sales: int = 0
    rating: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    discounted_price: Optional[Decimal] = None
    offer_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("retail_price", "cost_price")
    def serialize_prices(self, value: Decimal) -> str:
        return f"{value:.2f}"

    @field_serializer("discount_percentage", "discounted_price", "rating")
    def serialize_optional_decimal_fields(self, value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
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


class ProductMonthlySalesItem(BaseModel):
    month: str
    quantity_sold: int
    revenue: Decimal

    @field_serializer("revenue")
    def serialize_revenue(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ProductMonthlySalesResponse(BaseModel):
    product_id: int
    data: list[ProductMonthlySalesItem]
    count: int


class ProductReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ProductReviewResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    customer_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime


class ProductReviewsResponse(BaseModel):
    product_id: int
    data: list[ProductReviewResponse]
    count: int
    average_rating: Optional[Decimal] = None

    @field_serializer("average_rating")
    def serialize_average_rating(self, value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
        return f"{value:.2f}"


class CategoryNewProductsItem(BaseModel):
    id: int
    name: str
    slug: str
    new_products_count: int


class CategoriesWithNewProductsResponse(BaseModel):
    data: list[CategoryNewProductsItem]
    count: int
