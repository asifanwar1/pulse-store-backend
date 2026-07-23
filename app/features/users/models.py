from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from enum import Enum as PyEnum


class UserType(PyEnum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    VENDOR = "VENDOR"


class UserStatus(PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


def default_address() -> dict:
    return {
        "street_address": "",
        "city": "",
        "country": "",
        "state": "",
        "zipcode": "",
        "latitude": "",
        "longitude": "",
    }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    address = Column(JSON, nullable=False, default=default_address)
    user_type = Column(String, nullable=False, default=UserType.CUSTOMER)
    status = Column(String, nullable=False, default=UserStatus.ACTIVE.value)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    token_version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)
    product_reviews = relationship("ProductReview", back_populates="user")

    @property
    def is_admin(self) -> bool:
        return self.user_type == UserType.ADMIN.value
