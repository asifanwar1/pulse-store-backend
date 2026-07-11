from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.features.media.schemas import MediaItem


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image: Optional[MediaItem] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image: Optional[MediaItem] = None


class CategoryResponse(CategoryBase):
    id: int
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    data: list[CategoryResponse]
    count: int
