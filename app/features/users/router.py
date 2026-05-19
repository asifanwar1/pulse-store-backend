from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.users import service
from app.features.users.schemas import (
    UserListResponse,
    UserResponse,
    UserSortDirection,
    UserStatusFilter,
    UserStatusUpdate,
    UserTypeFilter,
    UserUpdate,
)
from app.features.auth.dependencies import get_current_user, get_current_admin_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(user_in: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.update_user(db, current_user.id, user_in)


@router.get("/", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    column: str = Query("created_at"),
    direction: UserSortDirection = Query(UserSortDirection.DESC),
    search: Optional[str] = Query(None),
    status: Optional[UserStatusFilter] = Query(None),
    user_type: Optional[UserTypeFilter] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_users(
        db,
        page=page,
        limit=limit,
        column=column,
        direction=direction,
        search=search,
        status=status,
        user_type=user_type,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_user_by_id(db, user_id)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.update_user_status(db, user_id, status_in)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_user(db, user_id)
