import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class OfferScope(str, enum.Enum):
    ALL_CATEGORIES = "ALL_CATEGORIES"
    SPECIFIC_CATEGORIES = "SPECIFIC_CATEGORIES"


offer_categories = Table(
    "offer_categories",
    Base.metadata,
    Column("offer_id", Integer, ForeignKey("offers.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
)


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    scope = Column(Enum(OfferScope), nullable=False, default=OfferScope.SPECIFIC_CATEGORIES)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    categories = relationship("Category", secondary=offer_categories)
    product_links = relationship("OfferProduct", back_populates="offer", cascade="all, delete-orphan")

    @property
    def status(self) -> str:
        if not self.is_active:
            return "DISABLED"
        now = datetime.now(timezone.utc)
        if now < self.start_date:
            return "UPCOMING"
        if now > self.end_date:
            return "EXPIRED"
        return "ACTIVE"


class OfferProduct(Base):
    __tablename__ = "offer_products"

    offer_id = Column(Integer, ForeignKey("offers.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    is_excluded = Column(Boolean, nullable=False, default=False)

    offer = relationship("Offer", back_populates="product_links")
    product = relationship("Product")
