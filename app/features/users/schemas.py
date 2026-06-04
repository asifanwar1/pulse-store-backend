from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserType(str, Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    VENDOR = "VENDOR"


class UserSortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class UserStatusFilter(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class UserTypeFilter(str, Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"


class Address(BaseModel):
    street_address: str = ""
    city: str = ""
    country: str = ""
    state: str = ""
    zipcode: str = ""
    latitude: str = ""
    longitude: str = ""


class UserBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    full_name: str = Field(alias="fullName")
    phone_number: Optional[str] = Field(default=None, alias="phoneNumber")
    address: Address = Field(default_factory=Address)
    user_type: UserType = Field(default=UserType.CUSTOMER, alias="userType")


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: Optional[str] = None
    full_name: Optional[str] = Field(default=None, alias="fullName")
    phone_number: Optional[str] = Field(default=None, alias="phoneNumber")
    address: Optional[Address] = None
    user_type: Optional[str] = Field(default=None, alias="userType")
    password: Optional[str] = None


class UserStatusUpdate(BaseModel):
    status: UserStatusFilter


class UserResponse(UserBase):
    id: int
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserListResponse(BaseModel):
    data: list[UserResponse]
    count: int
