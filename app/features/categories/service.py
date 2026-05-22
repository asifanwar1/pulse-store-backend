from sqlalchemy.orm import Session
from app.features.categories.models import Category
from app.features.categories.schemas import CategoryCreate, CategoryUpdate
from app.core.exceptions import NotFoundException, ConflictException


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
    if db.query(Category).filter(Category.slug == category_in.slug).first():
        raise ConflictException("Category slug already exists")
    category = Category(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, category_in: CategoryUpdate) -> Category:
    category = get_category_by_id(db, category_id)
    for field, value in category_in.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category_by_id(db, category_id)
    db.delete(category)
    db.commit()
