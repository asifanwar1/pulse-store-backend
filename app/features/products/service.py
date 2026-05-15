from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.features.categories.models import Category
from app.features.products.models import Product
from app.features.products.schemas import (
    ProductCategoryFilter,
    ProductCreate,
    ProductSortDirection,
    ProductStatusFilter,
    ProductUpdate,
)
from app.core.exceptions import NotFoundException, ConflictException


SORTABLE_PRODUCT_COLUMNS = {
    "id": Product.id,
    "name": Product.name,
    "slug": Product.slug,
    "price": Product.price,
    "stock_quantity": Product.stock_quantity,
    "created_at": Product.created_at,
    "updated_at": Product.updated_at,
}


def get_products(
    db: Session,
    page: int = 1,
    limit: int = 10,
    column: str = "created_at",
    direction: ProductSortDirection = ProductSortDirection.DESC,
    search: Optional[str] = None,
    status: Optional[ProductStatusFilter] = None,
    category: Optional[ProductCategoryFilter] = None,
    category_id: Optional[int] = None,
) -> list[Product]:
    query = db.query(Product).outerjoin(Category)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Product.slug.ilike(search_term),
                    Product.description.ilike(search_term),
                    Category.name.ilike(search_term),
                )
            )

    if status == ProductStatusFilter.ACTIVE:
        query = query.filter(Product.is_active.is_(True), Product.stock_quantity > 0)
    elif status == ProductStatusFilter.DRAFT:
        query = query.filter(Product.is_active.is_(False))
    elif status == ProductStatusFilter.OUT_OF_STOCK:
        query = query.filter(Product.stock_quantity <= 0)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if category is not None:
        query = query.filter(Category.name.ilike(category.value))

    sort_column = SORTABLE_PRODUCT_COLUMNS.get(column, Product.created_at)
    if direction == ProductSortDirection.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * limit
    return query.offset(offset).limit(limit).all()


def get_product_by_id(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundException("Product not found")
    return product


def create_product(db: Session, product_in: ProductCreate) -> Product:
    if db.query(Product).filter(Product.slug == product_in.slug).first():
        raise ConflictException("Product slug already exists")
    product = Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, product_in: ProductUpdate) -> Product:
    product = get_product_by_id(db, product_id)
    for field, value in product_in.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product_by_id(db, product_id)
    db.delete(product)
    db.commit()
