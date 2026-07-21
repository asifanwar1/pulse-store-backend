from decimal import ROUND_HALF_UP, Decimal
from pydantic import BaseModel, field_serializer, model_validator
from typing import Optional

from app.features.products.schemas import ProductResponse


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: Optional[ProductResponse] = None
    product_name: str = ""
    price: Decimal = Decimal("0")
    subtotal: Decimal = Decimal("0")

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_derived_fields(self):
        if self.product is not None:
            self.product_name = self.product.name
            # Effective price mirrors orders/service.py's create_order: prefer
            # the product's active discounted price, falling back to retail price.
            self.price = (
                self.product.discounted_price
                if self.product.discounted_price is not None
                else self.product.retail_price
            )
            self.subtotal = (self.price * self.quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return self

    @field_serializer("price", "subtotal")
    def serialize_price_fields(self, value: Decimal) -> str:
        return f"{value:.2f}"


class CartResponse(BaseModel):
    id: int
    user_id: int
    items: list[CartItemResponse] = []
    total_items: int = 0
    total_price: Decimal = Decimal("0")

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_totals(self):
        self.total_items = sum(item.quantity for item in self.items)
        self.total_price = sum((item.subtotal for item in self.items), Decimal("0"))
        return self

    @field_serializer("total_price")
    def serialize_total_price(self, value: Decimal) -> str:
        return f"{value:.2f}"
