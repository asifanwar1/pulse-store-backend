from sqlalchemy.orm import Session
from app.features.categories.models import Category
from app.features.categories.schemas import CategoryCreate, CategoryUpdate
from app.core.exceptions import NotFoundException, ConflictException


def get_categories(db: Session, skip: int = 0, limit: int = 100) -> list[Category]:
    return db.query(Category).offset(skip).limit(limit).all()


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
