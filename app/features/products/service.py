from typing import Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.features.orders.models import Order, OrderItem, OrderStatus
from app.features.categories.models import Category
from app.features.products.models import Product, ProductReview
from app.features.products.schemas import (
    ProductAnalyticsMetric,
    ProductAnalyticsResponse,
    ProductCategoryFilter,
    ProductCreate,
    ProductMonthlySalesItem,
    ProductMonthlySalesResponse,
    ProductReviewsResponse,
    ProductReviewResponse,
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


def _require_category_id(db: Session, category_id: int) -> int:
    category_record = db.query(Category).filter(Category.id == category_id).first()
    if not category_record:
        raise NotFoundException(f"Category {category_id} not found")
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


def _calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        if current == 0:
            return Decimal("0.00")
        return Decimal("100.00")
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_products_analytics(db: Session) -> ProductAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)

    all_products = db.query(Product).all()
    previous_products = [product for product in all_products if product.created_at and product.created_at < period_start]

    current_total = Decimal(len(all_products))
    previous_total = Decimal(len(previous_products))

    current_active = Decimal(sum(1 for product in all_products if product.is_active and product.stock_quantity > 0))
    previous_active = Decimal(sum(1 for product in previous_products if product.is_active and product.stock_quantity > 0))

    current_out_of_stock = Decimal(sum(1 for product in all_products if product.stock_quantity <= 0))
    previous_out_of_stock = Decimal(sum(1 for product in previous_products if product.stock_quantity <= 0))

    current_average_price = (
        sum((_to_decimal(product.price) for product in all_products), Decimal("0")) / current_total
        if all_products
        else Decimal("0")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    previous_average_price = (
        sum((_to_decimal(product.price) for product in previous_products), Decimal("0")) / previous_total
        if previous_products
        else Decimal("0")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return ProductAnalyticsResponse(
        total_products=ProductAnalyticsMetric(
            value=int(current_total),
            change_percentage=_calculate_percentage_change(current_total, previous_total),
        ),
        active_products=ProductAnalyticsMetric(
            value=int(current_active),
            change_percentage=_calculate_percentage_change(current_active, previous_active),
        ),
        out_of_stock_products=ProductAnalyticsMetric(
            value=int(current_out_of_stock),
            change_percentage=_calculate_percentage_change(current_out_of_stock, previous_out_of_stock),
        ),
        average_price=ProductAnalyticsMetric(
            value=current_average_price,
            change_percentage=_calculate_percentage_change(current_average_price, previous_average_price),
        ),
    )


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
) -> dict:
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

    total_count = query.count()

    sort_column = SORTABLE_PRODUCT_COLUMNS.get(column, Product.created_at)
    if direction == ProductSortDirection.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    return {"data": products, "count": total_count}


def get_product_by_id(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundException("Product not found")
    return product


def get_product_monthly_sales(db: Session, product_id: int) -> ProductMonthlySalesResponse:
    get_product_by_id(db, product_id)

    order_items = (
        db.query(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id == product_id, Order.status != OrderStatus.CANCELLED)
        .all()
    )

    monthly_sales: dict[str, dict[str, Decimal | int]] = {}
    for order_item, order in order_items:
        if not order.created_at:
            continue
        month = order.created_at.strftime("%Y-%m")
        if month not in monthly_sales:
            monthly_sales[month] = {"quantity_sold": 0, "revenue": Decimal("0")}
        monthly_sales[month]["quantity_sold"] += order_item.quantity
        monthly_sales[month]["revenue"] += _to_decimal(order_item.unit_price) * Decimal(order_item.quantity)

    data = [
        ProductMonthlySalesItem(
            month=month,
            quantity_sold=int(values["quantity_sold"]),
            revenue=_to_decimal(values["revenue"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        for month, values in sorted(monthly_sales.items())
    ]

    return ProductMonthlySalesResponse(product_id=product_id, data=data, count=len(data))


def get_product_customer_reviews(db: Session, product_id: int) -> ProductReviewsResponse:
    get_product_by_id(db, product_id)

    reviews = (
        db.query(ProductReview)
        .filter(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
        .all()
    )

    average_rating = None
    if reviews:
        average_rating = (
            sum((Decimal(review.rating) for review in reviews), Decimal("0")) / Decimal(len(reviews))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    data = [
        ProductReviewResponse(
            id=review.id,
            product_id=review.product_id,
            user_id=review.user_id,
            customer_name=review.user.full_name,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
        )
        for review in reviews
    ]

    return ProductReviewsResponse(product_id=product_id, data=data, count=len(data), average_rating=average_rating)


def create_product(db: Session, product_in: ProductCreate) -> Product:
    if db.query(Product).filter(Product.sku == product_in.sku).first():
        raise ConflictException("Product SKU already exists")

    slug = _generate_product_slug(product_in.name, product_in.sku)
    if db.query(Product).filter(Product.slug == slug).first():
        raise ConflictException("Generated product slug already exists")

    category_id = _require_category_id(db, product_in.category_id)
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
        product.category_id = _require_category_id(db, update_data["category_id"])
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
