from pydantic import BaseModel
from app.features.products.schemas import ProductResponse


class FavouriteToggleResponse(BaseModel):
    product_id: int
    is_favourited: bool


class FavouriteListResponse(BaseModel):
    data: list[ProductResponse]
    count: int
