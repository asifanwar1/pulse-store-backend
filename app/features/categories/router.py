from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.categories import service
from app.features.categories.schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from app.features.auth.dependencies import get_current_admin_user

router = APIRouter()


@router.get("/", response_model=list[CategoryResponse])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return service.get_categories(db, skip=skip, limit=limit)


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_category(db, category_in)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    return service.get_category_by_id(db, category_id)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category_in: CategoryUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_category(db, category_id, category_in)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_category(db, category_id)
