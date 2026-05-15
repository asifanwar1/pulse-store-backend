from enum import Enum
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    price: Decimal
    stock_quantity: int = 0
    category_id: Optional[int] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


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
