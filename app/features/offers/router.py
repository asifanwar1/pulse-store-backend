from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.offers import service
from app.features.offers.models import OfferScope
from app.features.offers.schemas import (
    ActiveOffersListResponse,
    OfferCreate,
    OfferListResponse,
    OfferResponse,
    OfferStatus,
    OfferUpdate,
)

router = APIRouter()


@router.get("/", response_model=OfferListResponse)
def list_offers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    scope: Optional[OfferScope] = Query(None),
    is_active: Optional[bool] = Query(None),
    status: Optional[OfferStatus] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_offers(
        db,
        page=page,
        limit=limit,
        search=search,
        scope=scope,
        is_active=is_active,
        status=status,
    )


@router.get("/active", response_model=ActiveOffersListResponse)
def list_active_offers(db: Session = Depends(get_db)):
    return service.get_active_offers(db)


@router.post("/", response_model=OfferResponse, status_code=201)
def create_offer(offer_in: OfferCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_offer(db, offer_in)


@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(offer_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_offer_by_id(db, offer_id)


@router.patch("/{offer_id}", response_model=OfferResponse)
def update_offer(offer_id: int, offer_in: OfferUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_offer(db, offer_id, offer_in)


@router.delete("/{offer_id}", status_code=204)
def delete_offer(offer_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_offer(db, offer_id)
