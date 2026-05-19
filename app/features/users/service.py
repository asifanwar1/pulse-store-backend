from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.features.users.models import User
from app.features.users.schemas import UserSortDirection, UserStatusFilter, UserStatusUpdate, UserTypeFilter, UserUpdate
from app.core.security import hash_password
from app.core.exceptions import NotFoundException


SORTABLE_USER_COLUMNS = {
    "id": User.id,
    "email": User.email,
    "full_name": User.full_name,
    "phone_number": User.phone_number,
    "user_type": User.user_type,
    "is_active": User.is_active,
    "created_at": User.created_at,
    "updated_at": User.updated_at,
}


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_users(
    db: Session,
    page: int = 1,
    limit: int = 10,
    column: str = "created_at",
    direction: UserSortDirection = UserSortDirection.DESC,
    search: Optional[str] = None,
    status: Optional[UserStatusFilter] = None,
    user_type: Optional[UserTypeFilter] = None,
) -> dict:
    query = db.query(User)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.phone_number.ilike(search_term),
                    User.user_type.ilike(search_term),
                )
            )

    if status == UserStatusFilter.ACTIVE:
        query = query.filter(User.is_active.is_(True))
    elif status == UserStatusFilter.INACTIVE:
        query = query.filter(User.is_active.is_(False))

    if user_type is not None:
        query = query.filter(User.user_type == user_type.value)

    total_count = query.count()

    sort_column = SORTABLE_USER_COLUMNS.get(column, User.created_at)
    if direction == UserSortDirection.ASC:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    return {"data": users, "count": total_count}


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    if user_in.email is not None:
        user.email = user_in.email
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.phone_number is not None:
        user.phone_number = user_in.phone_number
    if user_in.user_type is not None:
        user.user_type = user_in.user_type
    if user_in.password is not None:
        user.hashed_password = hash_password(user_in.password)
    db.commit()
    db.refresh(user)
    return user


def update_user_status(db: Session, user_id: int, status_in: UserStatusUpdate) -> User:
    user = get_user_by_id(db, user_id)
    user.is_active = status_in.status == UserStatusFilter.ACTIVE
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    db.delete(user)
    db.commit()
