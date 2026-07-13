from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.features.banners.models import LinkType, Placement


class BannerBase(BaseModel):
    title: str
    link_type: LinkType
    link_value: Optional[str] = None
    placement: Placement
    position: int = 0
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class BannerCreate(BannerBase):
    image_url: str
    image_url_mobile: Optional[str] = None
    design_json: dict

    @field_validator("design_json")
    @classmethod
    def validate_design_json(cls, value: dict) -> dict:
        if not value:
            raise ValueError("design_json must not be empty")
        return value


class BannerUpdate(BaseModel):
    title: Optional[str] = None
    image_url: Optional[str] = None
    image_url_mobile: Optional[str] = None
    design_json: Optional[dict] = None
    link_type: Optional[LinkType] = None
    link_value: Optional[str] = None
    placement: Optional[Placement] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("design_json")
    @classmethod
    def validate_design_json(cls, value: Optional[dict]) -> Optional[dict]:
        if value is not None and not value:
            raise ValueError("design_json must not be empty")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class BannerResponse(BaseModel):
    id: int
    title: str
    image_url: str
    image_url_mobile: Optional[str] = None
    design_json: dict
    link_type: LinkType
    link_value: Optional[str] = None
    placement: Placement
    position: int
    is_active: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    model_config = {"from_attributes": True}


class BannerListResponse(BaseModel):
    data: list[BannerResponse]
    count: int


class BannerStatusUpdate(BaseModel):
    is_active: bool = Field(...)


class BannerPublicOut(BaseModel):
    """Display-only shape for the public/consumer endpoint. Never includes design_json."""

    id: int
    image_url: str
    image_url_mobile: Optional[str] = None
    link_type: LinkType
    link_value: Optional[str] = None
    placement: Placement
    position: int

    model_config = {"from_attributes": True}


class ActiveBannersListResponse(BaseModel):
    data: list[BannerPublicOut]
    count: int
