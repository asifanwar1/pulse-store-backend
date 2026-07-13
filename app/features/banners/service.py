import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.features.banners.models import Banner, LinkType, Placement
from app.features.banners.schemas import BannerCreate, BannerStatusUpdate, BannerUpdate
from app.features.categories.models import Category
from app.features.products.models import Product

logger = logging.getLogger(__name__)


def _warn_if_link_value_missing(db: Session, link_type: LinkType, link_value: Optional[str]) -> None:
    if link_type not in (LinkType.PRODUCT, LinkType.CATEGORY) or not link_value:
        return

    try:
        referenced_id = int(link_value)
    except (TypeError, ValueError):
        logger.warning("Banner link_value %r is not a valid id for link_type=%s", link_value, link_type.value)
        return

    model = Product if link_type == LinkType.PRODUCT else Category
    exists = db.query(model.id).filter(model.id == referenced_id).first()
    if not exists:
        logger.warning("Banner link_value=%s does not match any existing %s", referenced_id, link_type.value)


def _validate_date_window(start_date: Optional[datetime], end_date: Optional[datetime]) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be before end_date",
        )


def get_banners(
    db: Session,
    page: int = 1,
    limit: int = 10,
    placement: Optional[Placement] = None,
    is_active: Optional[bool] = None,
) -> dict:
    query = db.query(Banner)

    if placement is not None:
        query = query.filter(Banner.placement == placement)
    if is_active is not None:
        query = query.filter(Banner.is_active.is_(is_active))

    total_count = query.count()
    offset = (page - 1) * limit
    banners = (
        query.order_by(Banner.placement, Banner.position, Banner.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"data": banners, "count": total_count}


def get_banner_by_id(db: Session, banner_id: int) -> Banner:
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise NotFoundException("Banner not found")
    return banner


def create_banner(db: Session, banner_in: BannerCreate, created_by: Optional[int] = None) -> Banner:
    _validate_date_window(banner_in.start_date, banner_in.end_date)
    _warn_if_link_value_missing(db, banner_in.link_type, banner_in.link_value)

    banner = Banner(**banner_in.model_dump(), created_by=created_by)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


def update_banner(db: Session, banner_id: int, banner_in: BannerUpdate) -> Banner:
    banner = get_banner_by_id(db, banner_id)
    update_data = banner_in.model_dump(exclude_unset=True)

    merged_start = update_data.get("start_date", banner.start_date)
    merged_end = update_data.get("end_date", banner.end_date)
    _validate_date_window(merged_start, merged_end)

    if "link_type" in update_data or "link_value" in update_data:
        link_type = update_data.get("link_type", banner.link_type)
        link_value = update_data.get("link_value", banner.link_value)
        _warn_if_link_value_missing(db, link_type, link_value)

    for field, value in update_data.items():
        setattr(banner, field, value)

    db.commit()
    db.refresh(banner)
    return banner


def delete_banner(db: Session, banner_id: int) -> None:
    banner = get_banner_by_id(db, banner_id)
    db.delete(banner)
    db.commit()


def set_banner_status(db: Session, banner_id: int, status_in: BannerStatusUpdate) -> Banner:
    banner = get_banner_by_id(db, banner_id)
    banner.is_active = status_in.is_active
    db.commit()
    db.refresh(banner)
    return banner


def get_active_banners(db: Session, placement: Placement) -> dict:
    now = datetime.now(timezone.utc)
    banners = (
        db.query(Banner)
        .filter(
            Banner.is_active.is_(True),
            Banner.placement == placement,
            or_(Banner.start_date.is_(None), Banner.start_date <= now),
            or_(Banner.end_date.is_(None), Banner.end_date >= now),
        )
        .order_by(Banner.position, Banner.id)
        .all()
    )
    return {"data": banners, "count": len(banners)}
