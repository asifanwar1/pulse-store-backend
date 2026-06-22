from typing import Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.features.orders.models import Order
from app.features.users.models import User, UserStatus
from app.features.users.schemas import (
    UserAnalyticsMetric,
    UserAnalyticsResponse,
    UserSortDirection,
    UserStatusFilter,
    UserStatusUpdate,
    UserTypeFilter,
    UserUpdate,
)
from app.core.security import hash_password
from app.core.exceptions import NotFoundException


SORTABLE_USER_COLUMNS = {
    "id": User.id,
    "email": User.email,
    "full_name": User.full_name,
    "phone_number": User.phone_number,
    "user_type": User.user_type,
    "status": User.status,
    "is_active": User.is_active,
    "created_at": User.created_at,
    "updated_at": User.updated_at,
}


def _calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        if current == 0:
            return Decimal("0.00")
        return Decimal("100.00")
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _attach_order_stats(db: Session, users: list[User]) -> list[User]:
    user_ids = [user.id for user in users]
    if not user_ids:
        return users

    rows = (
        db.query(
            Order.user_id,
            func.count(Order.id).label("total_orders"),
            func.max(Order.created_at).label("last_order"),
        )
        .filter(Order.user_id.in_(user_ids))
        .group_by(Order.user_id)
        .all()
    )
    stats_by_user_id = {
        user_id: (int(total_orders), last_order)
        for user_id, total_orders, last_order in rows
    }

    for user in users:
        total_orders, last_order = stats_by_user_id.get(user.id, (0, None))
        user.total_orders = total_orders
        user.last_order = last_order

    return users


def get_users_analytics(db: Session) -> UserAnalyticsResponse:
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    previous_period_start = period_start - timedelta(days=30)

    customer_query = db.query(User).filter(func.lower(User.user_type) == "customer")
    customers = customer_query.all()
    previous_customers = [
        customer
        for customer in customers
        if customer.created_at and customer.created_at < period_start
    ]

    customer_ids = [customer.id for customer in customers]
    previous_customer_ids = [customer.id for customer in previous_customers]

    active_customer_ids = set()
    previous_active_customer_ids = set()
    if customer_ids:
        active_customer_ids = {
            user_id
            for (user_id,) in (
                db.query(Order.user_id)
                .filter(Order.user_id.in_(customer_ids), Order.created_at >= period_start)
                .distinct()
                .all()
            )
        }
    if previous_customer_ids:
        previous_active_customer_ids = {
            user_id
            for (user_id,) in (
                db.query(Order.user_id)
                .filter(
                    Order.user_id.in_(previous_customer_ids),
                    Order.created_at >= previous_period_start,
                    Order.created_at < period_start,
                )
                .distinct()
                .all()
            )
        }

    non_blocked_customer_ids = {
        customer.id
        for customer in customers
        if customer.status != UserStatus.BLOCKED.value
    }
    previous_non_blocked_customer_ids = {
        customer.id
        for customer in previous_customers
        if customer.status != UserStatus.BLOCKED.value
    }

    current_total = Decimal(len(customers))
    previous_total = Decimal(len(previous_customers))

    current_active = Decimal(len(active_customer_ids & non_blocked_customer_ids))
    previous_active = Decimal(len(previous_active_customer_ids & previous_non_blocked_customer_ids))

    current_blocked = Decimal(sum(1 for customer in customers if customer.status == UserStatus.BLOCKED.value))
    previous_blocked = Decimal(
        sum(1 for customer in previous_customers if customer.status == UserStatus.BLOCKED.value)
    )

    current_inactive = Decimal(len(non_blocked_customer_ids) - int(current_active))
    previous_inactive = Decimal(len(previous_non_blocked_customer_ids) - int(previous_active))

    return UserAnalyticsResponse(
        totalCustomers=UserAnalyticsMetric(
            value=int(current_total),
            change_percentage=_calculate_percentage_change(current_total, previous_total),
        ),
        activeCustomers=UserAnalyticsMetric(
            value=int(current_active),
            change_percentage=_calculate_percentage_change(current_active, previous_active),
        ),
        InactiveCustomer=UserAnalyticsMetric(
            value=int(current_inactive),
            change_percentage=_calculate_percentage_change(current_inactive, previous_inactive),
        ),
        blockedCustomer=UserAnalyticsMetric(
            value=int(current_blocked),
            change_percentage=_calculate_percentage_change(current_blocked, previous_blocked),
        ),
    )


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    return _attach_order_stats(db, [user])[0]


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

    if status is not None:
        query = query.filter(User.status == status.value)

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
    _attach_order_stats(db, users)
    return {"data": users, "count": total_count}


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    if user_in.email is not None:
        user.email = user_in.email
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.phone_number is not None:
        user.phone_number = user_in.phone_number
    if user_in.address is not None:
        current_address = user.address if isinstance(user.address, dict) else {}
        address_updates = user_in.address.model_dump(exclude_unset=True, exclude_none=True)
        user.address = {**current_address, **address_updates}
    if user_in.user_type is not None:
        user.user_type = user_in.user_type
    if user_in.password is not None:
        user.hashed_password = hash_password(user_in.password)
    db.commit()
    db.refresh(user)
    return _attach_order_stats(db, [user])[0]


def update_user_status(db: Session, user_id: int, status_in: UserStatusUpdate) -> User:
    user = get_user_by_id(db, user_id)
    user.status = status_in.status.value
    user.is_active = status_in.status == UserStatusFilter.ACTIVE
    db.commit()
    db.refresh(user)
    return _attach_order_stats(db, [user])[0]


def delete_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    db.delete(user)
    db.commit()
