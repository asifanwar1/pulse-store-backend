import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class LinkType(str, enum.Enum):
    PRODUCT = "product"
    CATEGORY = "category"
    URL = "url"
    NONE = "none"


class Placement(str, enum.Enum):
    HOME_TOP = "home_top"
    HOME_MID = "home_mid"
    CATEGORY_PAGE = "category_page"


# Member names are uppercase (project convention) but values are the lowercase
# wire format the frontend sends, so values_callable is required or SQLAlchemy
# would persist the member name ("PRODUCT") instead of the value ("product").
def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class Banner(Base):
    __tablename__ = "banners"
    __table_args__ = (
        Index("ix_banners_placement_active_position", "placement", "is_active", "position"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)

    # The flattened, ready-to-display image the frontend renders on web/mobile.
    image_url = Column(String, nullable=False)
    image_url_mobile = Column(String, nullable=True)

    # Editable canvas state from the admin banner editor. Opaque to the backend.
    design_json = Column(JSONB, nullable=False)

    link_type = Column(
        Enum(LinkType, name="banner_link_type", native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
    )
    link_value = Column(String, nullable=True)

    placement = Column(
        Enum(Placement, name="banner_placement", native_enum=False, length=50, values_callable=_enum_values),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
