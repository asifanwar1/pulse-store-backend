from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.banners import service
from app.features.banners.models import Placement
from app.features.banners.schemas import (
    ActiveBannersListResponse,
    BannerCreate,
    BannerListResponse,
    BannerResponse,
    BannerStatusUpdate,
    BannerUpdate,
)
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=BannerListResponse)
def list_banners(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    placement: Optional[Placement] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_banners(db, page=page, limit=limit, placement=placement, is_active=is_active)


@router.get("/active", response_model=ActiveBannersListResponse)
def list_active_banners(
    placement: Placement = Query(...),
    db: Session = Depends(get_db),
):
    return service.get_active_banners(db, placement)


@router.post("/", response_model=BannerResponse, status_code=201)
def create_banner(
    banner_in: BannerCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.create_banner(db, banner_in, created_by=current_admin.id)


@router.get("/{banner_id}", response_model=BannerResponse)
def get_banner(banner_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_banner_by_id(db, banner_id)


@router.put("/{banner_id}", response_model=BannerResponse)
def update_banner(
    banner_id: int,
    banner_in: BannerUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.update_banner(db, banner_id, banner_in)


@router.patch("/{banner_id}/status", response_model=BannerResponse)
def update_banner_status(
    banner_id: int,
    status_in: BannerStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.set_banner_status(db, banner_id, status_in)


@router.delete("/{banner_id}", status_code=204)
def delete_banner(banner_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_banner(db, banner_id)
