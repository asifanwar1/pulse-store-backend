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
from app.core.exceptions import BadRequestException, NotFoundException, ConflictException
import re


SORTABLE_PRODUCT_COLUMNS = {
    "id": Product.id,
    "name": Product.name,
    "sku": Product.sku,
    "brand": Product.brand,
    "slug": Product.slug,
    "price": Product.price,
    "cost_price": Product.cost_price,
    "stock_quantity": Product.stock_quantity,
    "created_at": Product.created_at,
    "updated_at": Product.updated_at,
}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


def _generate_product_slug(name: str, sku: str) -> str:
    return _slugify(f"{name}-{sku}")


def _resolve_category_id(db: Session, category: ProductCategoryFilter) -> int:
    category_record = db.query(Category).filter(Category.name.ilike(category.value)).first()
    if not category_record:
        raise NotFoundException(f"Category {category.value} not found")
    return category_record.id


def _status_to_flags(status: ProductStatusFilter, stock_quantity: int) -> bool:
    if status == ProductStatusFilter.ACTIVE:
        if stock_quantity <= 0:
            raise BadRequestException("stock_quantity must be greater than 0 when status is ACTIVE")
        return True
    if status == ProductStatusFilter.DRAFT:
        return False
    if stock_quantity > 0:
        raise BadRequestException("stock_quantity must be 0 when status is OUT_OF_STOCK")
    return True


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
                Product.sku.ilike(search_term),
                Product.brand.ilike(search_term),
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
    if db.query(Product).filter(Product.sku == product_in.sku).first():
        raise ConflictException("Product SKU already exists")

    slug = _generate_product_slug(product_in.name, product_in.sku)
    if db.query(Product).filter(Product.slug == slug).first():
        raise ConflictException("Generated product slug already exists")

    category_id = _resolve_category_id(db, product_in.category)
    is_active = _status_to_flags(product_in.status, product_in.stock_quantity)

    product = Product(
        name=product_in.name,
        sku=product_in.sku,
        brand=product_in.brand,
        slug=slug,
        description=product_in.description,
        price=product_in.retail_price,
        cost_price=product_in.cost_price,
        stock_quantity=product_in.stock_quantity,
        tags=[tag.strip() for tag in product_in.tags if tag.strip()],
        media=[item.model_dump() for item in product_in.media],
        category_id=category_id,
        is_active=is_active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, product_in: ProductUpdate) -> Product:
    product = get_product_by_id(db, product_id)
    update_data = product_in.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] != product.sku:
        if db.query(Product).filter(Product.sku == update_data["sku"], Product.id != product.id).first():
            raise ConflictException("Product SKU already exists")
        product.sku = update_data["sku"]

    if "name" in update_data:
        product.name = update_data["name"]
    if "brand" in update_data:
        product.brand = update_data["brand"]
    if "description" in update_data:
        product.description = update_data["description"]
    if "retail_price" in update_data:
        product.price = update_data["retail_price"]
    if "cost_price" in update_data:
        product.cost_price = update_data["cost_price"]
    if "stock_quantity" in update_data:
        product.stock_quantity = update_data["stock_quantity"]
    if "tags" in update_data:
        product.tags = [tag.strip() for tag in update_data["tags"] if tag.strip()]
    if "media" in update_data:
        product.media = [item.model_dump() for item in product_in.media or []]
    if "category_id" in update_data:
        product.category_id = update_data["category_id"]
    if "category" in update_data and update_data["category"] is not None:
        product.category_id = _resolve_category_id(db, update_data["category"])
    if "status" in update_data and update_data["status"] is not None:
        product.is_active = _status_to_flags(update_data["status"], product.stock_quantity)

    generated_slug = _generate_product_slug(product.name, product.sku)
    if generated_slug != product.slug:
        if db.query(Product).filter(Product.slug == generated_slug, Product.id != product.id).first():
            raise ConflictException("Generated product slug already exists")
        product.slug = generated_slug

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product_by_id(db, product_id)
    db.delete(product)
    db.commit()
