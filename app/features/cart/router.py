from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.cart import service
from app.features.cart.schemas import CartItemAdd, CartItemUpdate, CartResponse
from app.features.auth.dependencies import get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=CartResponse)
def get_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.get_or_create_cart(db, current_user.id)


@router.post("/items", response_model=CartResponse)
def add_item(item_in: CartItemAdd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.add_item(db, current_user.id, item_in)


@router.put("/items/{item_id}", response_model=CartResponse)
def update_item(item_id: int, item_in: CartItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.update_item(db, current_user.id, item_id, item_in)


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.remove_item(db, current_user.id, item_id)


@router.delete("/", status_code=204)
def clear_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service.clear_cart(db, current_user.id)
