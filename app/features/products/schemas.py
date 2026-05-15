from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


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


class ProductMediaItem(BaseModel):
    id: str
    url: str


class ProductPayloadBase(BaseModel):
    name: str
    sku: str
    brand: str
    description: Optional[str] = None
    retail_price: Decimal
    cost_price: Decimal
    stock_quantity: int = 0
    tags: list[str] = Field(default_factory=list)
    media: list[ProductMediaItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status_stock_consistency(self):
        status = getattr(self, "status", None)
        if status == ProductStatusFilter.ACTIVE and self.stock_quantity <= 0:
            raise ValueError("stock_quantity must be greater than 0 when status is ACTIVE")
        if status == ProductStatusFilter.OUT_OF_STOCK and self.stock_quantity > 0:
            raise ValueError("stock_quantity must be 0 when status is OUT_OF_STOCK")
        return self


class ProductCreate(ProductPayloadBase):
    category: ProductCategoryFilter
    status: ProductStatusFilter


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    retail_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[int] = None
    category: Optional[ProductCategoryFilter] = None
    status: Optional[ProductStatusFilter] = None
    tags: Optional[list[str]] = None
    media: Optional[list[ProductMediaItem]] = None


class ProductResponse(ProductPayloadBase):
    id: int
    slug: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
