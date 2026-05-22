from sqlalchemy.orm import Session
from app.features.categories.models import Category
from app.features.categories.schemas import CategoryCreate, CategoryUpdate
from app.core.exceptions import NotFoundException
import re


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "category"


def _generate_unique_slug(db: Session, name: str, category_id: int | None = None) -> str:
    base_slug = _slugify(name)
    slug = base_slug
    counter = 2

    while True:
        query = db.query(Category).filter(Category.slug == slug)
        if category_id is not None:
            query = query.filter(Category.id != category_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def get_categories(
    db: Session,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
) -> dict:
    query = db.query(Category)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(
                Category.name.ilike(search_term) |
                Category.slug.ilike(search_term) |
                Category.description.ilike(search_term)
            )

    total_count = query.count()
    offset = (page - 1) * limit
    categories = query.order_by(Category.created_at.desc()).offset(offset).limit(limit).all()
    return {"data": categories, "count": total_count}


def get_category_by_id(db: Session, category_id: int) -> Category:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise NotFoundException("Category not found")
    return category


def create_category(db: Session, category_in: CategoryCreate) -> Category:
    slug = _generate_unique_slug(db, category_in.name)
    category = Category(**category_in.model_dump(), slug=slug)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, category_in: CategoryUpdate) -> Category:
    category = get_category_by_id(db, category_id)
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    if "name" in update_data:
        category.slug = _generate_unique_slug(db, category.name, category.id)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category_by_id(db, category_id)
    db.delete(category)
    db.commit()
