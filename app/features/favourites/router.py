from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.favourites import service
from app.features.favourites.schemas import FavouriteListResponse, FavouriteToggleResponse
from app.features.auth.dependencies import get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=FavouriteListResponse)
def get_favourites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.get_favourite_products(db, current_user.id)


@router.post("/{product_id}", response_model=FavouriteToggleResponse)
def toggle_favourite(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.toggle_favourite(db, current_user.id, product_id)
