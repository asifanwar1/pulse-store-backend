from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from enum import Enum as PyEnum


class UserType(PyEnum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    VENDOR = "VENDOR"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    user_type = Column(String, nullable=False, default=UserType.CUSTOMER)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)
    product_reviews = relationship("ProductReview", back_populates="user")

    @property
    def is_admin(self) -> bool:
        return self.user_type == UserType.ADMIN.value
