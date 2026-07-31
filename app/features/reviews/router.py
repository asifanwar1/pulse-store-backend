from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.reviews import service
from app.features.reviews.schemas import (
    MyReviewListResponse,
    ReviewAnalyticsResponse,
    ReviewListResponse,
    ReviewResponse,
    ReviewVisibilityUpdate,
)
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/me", response_model=MyReviewListResponse)
def get_my_reviews(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.get_my_reviews(db, current_user.id)


@router.get("/analytics", response_model=ReviewAnalyticsResponse)
def get_reviews_analytics(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_reviews_analytics(db)


@router.get("/", response_model=ReviewListResponse)
def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    product_id: Optional[int] = Query(None),
    rating: Optional[int] = Query(None, ge=1, le=5),
    is_hidden: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_reviews(
        db,
        page=page,
        limit=limit,
        product_id=product_id,
        rating=rating,
        is_hidden=is_hidden,
    )


@router.patch("/{review_id}/visibility", response_model=ReviewResponse)
def update_review_visibility(
    review_id: int,
    visibility_in: ReviewVisibilityUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.set_review_visibility(db, review_id, visibility_in)
