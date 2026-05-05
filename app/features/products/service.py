from typing import Optional
from sqlalchemy.orm import Session
from app.features.products.models import Product
from app.features.products.schemas import ProductCreate, ProductUpdate
from app.core.exceptions import NotFoundException, ConflictException


def get_products(db: Session, skip: int = 0, limit: int = 100, category_id: Optional[int] = None) -> list[Product]:
    query = db.query(Product).filter(Product.is_active == True)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    return query.offset(skip).limit(limit).all()


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
