from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_serializer, model_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
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
    BLOCKED = "BLOCKED"


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


class AddressUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    street_address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("zipcode", "zipCode", "zip_code"),
    )
    latitude: Optional[str] = None
    longitude: Optional[str] = None


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
    full_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("fullName", "full_name"),
    )
    phone_number: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("phoneNumber", "phone_number", "phone", "Phone"),
    )
    address: Optional[AddressUpdate] = None
    user_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("userType", "user_type"),
    )
    password: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def collect_address_fields(cls, data):
        if not isinstance(data, dict):
            return data

        address_keys = {
            "street_address",
            "city",
            "country",
            "state",
            "zipcode",
            "zipCode",
            "zip_code",
            "latitude",
            "longitude",
        }
        address = dict(data.get("address") or {})
        for key in address_keys:
            if key in data:
                address[key] = data[key]

        if address:
            return {**data, "address": address}
        return data


class UserStatusUpdate(BaseModel):
    status: UserStatusFilter


class UserResponse(UserBase):
    id: int
    status: UserStatusFilter
    total_orders: int = 0
    last_order: Optional[datetime] = None
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserListResponse(BaseModel):
    data: list[UserResponse]
    count: int


class UserAnalyticsMetric(BaseModel):
    value: int
    change_percentage: Decimal

    @field_serializer("change_percentage")
    def serialize_change_percentage(self, value: Decimal) -> str:
        return f"{value:.2f}"


class UserAnalyticsResponse(BaseModel):
    totalCustomers: UserAnalyticsMetric
    activeCustomers: UserAnalyticsMetric
    InactiveCustomer: UserAnalyticsMetric
    blockedCustomer: UserAnalyticsMetric
