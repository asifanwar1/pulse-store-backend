from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.products import service
from app.features.products.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.features.auth.dependencies import get_current_admin_user

router = APIRouter()


@router.get("/", response_model=list[ProductResponse])
def list_products(skip: int = 0, limit: int = 100, category_id: Optional[int] = None, db: Session = Depends(get_db)):
    return service.get_products(db, skip=skip, limit=limit, category_id=category_id)


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_product(db, product_in)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return service.get_product_by_id(db, product_id)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_product(db, product_id, product_in)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_product(db, product_id)
