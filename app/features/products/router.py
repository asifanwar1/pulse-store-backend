from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.products import service
from app.features.products.schemas import (
    CategoriesWithNewProductsResponse,
    ProductAnalyticsResponse,
    ProductCategoryFilter,
    ProductCreate,
    ProductListResponse,
    ProductMonthlySalesResponse,
    ProductResponse,
    ProductReviewCreate,
    ProductReviewResponse,
    ProductReviewsResponse,
    ProductSortDirection,
    ProductStatusFilter,
    ProductTotalSalesUpdate,
    ProductUpdate,
)
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    column: str = Query("created_at"),
    direction: ProductSortDirection = Query(ProductSortDirection.DESC),
    search: Optional[str] = Query(None),
    status: Optional[ProductStatusFilter] = Query(None),
    category: Optional[ProductCategoryFilter] = Query(None),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return service.get_products(
        db,
        page=page,
        limit=limit,
        column=column,
        direction=direction,
        search=search,
        status=status,
        category=category,
        category_id=category_id,
    )


@router.get("/analytics", response_model=ProductAnalyticsResponse)
def get_products_analytics(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_products_analytics(db)


@router.get("/categories/new-this-week", response_model=CategoriesWithNewProductsResponse)
def get_categories_with_new_products_this_week(db: Session = Depends(get_db)):
    return service.get_categories_with_new_products_this_week(db)


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_product(db, product_in)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return service.get_product_by_id(db, product_id)


@router.get("/{product_id}/monthly-sales", response_model=ProductMonthlySalesResponse)
def get_product_monthly_sales(product_id: int, db: Session = Depends(get_db)):
    return service.get_product_monthly_sales(db, product_id)


@router.get("/{product_id}/customer-reviews", response_model=ProductReviewsResponse)
def get_product_customer_reviews(product_id: int, db: Session = Depends(get_db)):
    return service.get_product_customer_reviews(db, product_id)


@router.post("/{product_id}/reviews", response_model=ProductReviewResponse)
def create_product_review(
    product_id: int,
    review_in: ProductReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.create_or_update_product_review(db, product_id, current_user.id, review_in)


@router.patch("/{product_id}/total-sales", response_model=ProductResponse)
def update_product_total_sales(product_id: int, sales_in: ProductTotalSalesUpdate, db: Session = Depends(get_db)):
    return service.update_product_total_sales(db, product_id, sales_in)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_product(db, product_id, product_in)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_product(db, product_id)
